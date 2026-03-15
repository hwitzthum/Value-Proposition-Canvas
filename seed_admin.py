#!/usr/bin/env python3
"""
Create the first admin user.

Usage:
    python seed_admin.py --email admin@example.com --password 'SecureP@ss1'

Or with prompts:
    python seed_admin.py
"""

import argparse
import getpass
import sys

from dotenv import load_dotenv

load_dotenv()

from app.database import get_db_context, create_tables  # noqa: E402
from app.auth import hash_password  # noqa: E402
from app.models import User  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Create the first admin user.")
    parser.add_argument("--email", help="Admin email address")
    parser.add_argument("--name", help="Display name", default="Admin")
    parser.add_argument("--password", help="Password (prompted if not provided)")
    args = parser.parse_args()

    email = args.email or input("Admin email: ").strip()
    if not email:
        print("Email is required.")
        sys.exit(1)

    name = args.name or input("Display name [Admin]: ").strip() or "Admin"
    password = args.password or getpass.getpass("Password: ")
    if len(password) < 10:
        print("Password must be at least 10 characters.")
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
