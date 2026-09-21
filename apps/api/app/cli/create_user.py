"""Operator command: create a user (registration is closed by default).

Usage:
    python -m app.cli.create_user --email you@example.com --password 'long-enough'
Run with MONGODB_URI set to provision users on the durable store; without it
the user lives only in process memory (useful for local smoke tests).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


async def _create(email: str, password: str) -> dict:
    from app.persistence.errors import ConflictError
    from app.persistence.store import get_store
    from app.security.passwords import hash_password

    email = email.strip().lower()
    if "@" not in email:
        raise SystemExit("error: enter a valid email")
    if len(password) < 8 or len(password) > 200:
        raise SystemExit("error: password must be 8..200 characters")
    store = get_store()
    await store.startup()
    try:
        try:
            user = await store.users.create(email, hash_password(password))
        except ConflictError:
            raise SystemExit("error: email taken")
        return user
    finally:
        await store.shutdown()


def main() -> None:
    ap = argparse.ArgumentParser(description="Create a user on the configured store.")
    ap.add_argument("--email", required=True)
    ap.add_argument("--password", required=True)
    args = ap.parse_args()
    user = asyncio.run(_create(args.email, args.password))
    print(f"created user {user['id']} ({user['email']})")


if __name__ == "__main__":
    main()
