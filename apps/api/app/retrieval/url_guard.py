"""URL guard: strict by default; refuses anything not globally routable.

Every resolved address of a hostname is checked (not just the first), after
unwrapping IPv4-mapped IPv6 forms. In production only the standard web ports
are allowed. The batch command opts out explicitly for local fixture sites.
The residual DNS-rebinding window (re-resolution between check and connect)
is documented, not closed.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

METADATA_IPS = {"169.254.169.254"}
SHARED_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def _unwrap(addr: ipaddress._BaseAddress) -> ipaddress._BaseAddress:
    mapped = getattr(addr, "ipv4_mapped", None)
    return mapped if mapped is not None else addr


def is_globally_routable(ip: str) -> bool:
    """True only for addresses safe to contact from production."""
    try:
        addr = _unwrap(ipaddress.ip_address(ip))
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv4Address) and addr in SHARED_CGNAT:
        return False
    if addr.is_multicast:
        return False
    if str(addr) in METADATA_IPS:
        return False
    return bool(addr.is_global)


def is_ip_private(ip: str) -> bool:
    """Legacy helper: True for anything that is not globally routable."""
    return not is_globally_routable(ip)


def validate_url(url: str, *, allow_private: bool = False, production: bool = False) -> tuple[bool, str]:
    """Return (ok, reason). Reasons: scheme|no-host|port|dns|private|unparseable."""
    try:
        parts = urlparse(url)
    except Exception:
        return False, "unparseable"
    if parts.scheme not in ("http", "https"):
        return False, "scheme"
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        return False, "no-host"
    if allow_private:
        return True, ""
    if production:
        port = parts.port
        default = 443 if parts.scheme == "https" else 80
        if port is not None and port != default:
            return False, "port"
    try:
        infos = socket.getaddrinfo(host, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False, "dns"
    if not infos:
        return False, "dns"
    for _fam, _type, _proto, _canon, sockaddr in infos:
        if not is_globally_routable(sockaddr[0]):
            return False, "private"
    return True, ""
