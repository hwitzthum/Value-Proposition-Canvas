#!/usr/bin/env python3
"""
Create the first admin user.

Usage (interactive):
    python seed_admin.py
    python seed_admin.py --email admin@example.com --name Admin

Usage (non-interactive, for deployment):
    python seed_admin.py --auto
    Reads ADMIN_EMAIL and ADMIN_PASSWORD from environment variables.
    Silently skips if env vars are missing or user already exists.
"""

import argparse
import getpass
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv()

from app.database import get_db_context, create_tables  # noqa: E402
from app.auth import hash_password  # noqa: E402
from app.models import User  # noqa: E402

_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{10,}$"
)


def _seed_from_env():
    """Non-interactive seeding from ADMIN_EMAIL / ADMIN_PASSWORD env vars."""
    email = os.getenv("ADMIN_EMAIL", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    name = os.getenv("ADMIN_NAME", "Admin").strip()

    if not email or not password:
        print("ADMIN_EMAIL or ADMIN_PASSWORD not set, skipping auto-seed.")
        return

    if not _PASSWORD_PATTERN.match(password):
        print("ADMIN_PASSWORD does not meet complexity requirements, skipping.")
        return

    with get_db_context() as db:
        existing = db.query(User).filter(User.email == email.lower()).first()
        if existing:
            print(f"Admin user '{email}' already exists, skipping seed.")
            return

        user = User(
            email=email.lower(),
            display_name=name,
            password_hash=hash_password(password),
            status="active",
            is_admin=True,
        )
        db.add(user)
        print(f"Admin user '{email}' created successfully.")


def main():
    parser = argparse.ArgumentParser(description="Create the first admin user.")
    parser.add_argument("--email", help="Admin email address")
    parser.add_argument("--name", help="Display name", default="Admin")
    parser.add_argument("--auto", action="store_true", help="Non-interactive mode using env vars")
    args = parser.parse_args()

    if args.auto:
        _seed_from_env()
        return

    email = args.email or input("Admin email: ").strip()
    if not email:
        print("Email is required.")
        sys.exit(1)

    name = args.name or input("Display name [Admin]: ").strip() or "Admin"

    # Always prompt for password interactively (never accept via CLI args)
    password = getpass.getpass("Password: ")
    if not _PASSWORD_PATTERN.match(password):
        print(
            "Password must be at least 10 characters and include "
            "uppercase, lowercase, digit, and special character."
        )
        sys.exit(1)

    # Ensure tables exist
    create_tables()

    with get_db_context() as db:
        existing = db.query(User).filter(User.email == email.lower()).first()
        if existing:
            print(f"User {email} already exists.")
            if not existing.is_admin:
                existing.is_admin = True
                existing.status = "active"
                print("Promoted to admin.")
            else:
                print("Already an admin.")
            return

        user = User(
            email=email.lower(),
            display_name=name,
            password_hash=hash_password(password),
            status="active",
            is_admin=True,
        )
        db.add(user)
        print(f"Admin user '{email}' created successfully.")


if __name__ == "__main__":
    main()
