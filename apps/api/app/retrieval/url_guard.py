"""URL guard: strict by default; rejects private/loopback/link-local/metadata."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

METADATA_IPS = {"169.254.169.254"}


def is_ip_private(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or str(addr) in METADATA_IPS


def validate_url(url: str, *, allow_private: bool = False) -> tuple[bool, str]:
    try:
        parts = urlparse(url)
    except Exception:
        return False, "unparseable"
    if parts.scheme not in ("http", "https"):
        return False, "scheme"
    if not parts.hostname:
        return False, "no-host"
    if allow_private:
        return True, ""
    try:
        infos = socket.getaddrinfo(parts.hostname, None, family=socket.AF_UNSPEC)
    except socket.gaierror:
        return False, "dns"
    for _fam, _type, _proto, _canon, sockaddr in infos:
        if is_ip_private(sockaddr[0]):
            return False, "private"
    return True, ""
