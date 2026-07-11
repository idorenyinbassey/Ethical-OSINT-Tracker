#!/usr/bin/env python
"""Reset admin user password - requires ADMIN_PASSWORD environment variable"""
import sys
import os

# Load variables from a .env file if present (optional dependency), so
# ADMIN_PASSWORD / DB_URL can be provided there rather than only via export.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from argon2 import PasswordHasher
from app.db import init_db, get_session
from app.models.user import User
from sqlmodel import select

ph = PasswordHasher()

# Check for required ADMIN_PASSWORD environment variable
admin_password = os.getenv("ADMIN_PASSWORD")
if not admin_password:
    print("❌ ERROR: ADMIN_PASSWORD environment variable not set")
    print("")
    print("Usage:")
    print("  ADMIN_PASSWORD=your_secure_password python reset_admin.py")
    print("")
    print("Security note: The admin password must be set via environment variable")
    print("and never hardcoded in scripts or version control.")
    sys.exit(1)

if len(admin_password) < 8:
    print("❌ ERROR: ADMIN_PASSWORD must be at least 8 characters long")
    sys.exit(1)

# Initialize database
init_db()

# Reset admin password
with get_session() as session:
    stmt = select(User).where(User.username == "admin")
    admin = session.exec(stmt).first()

    if admin:
        # Update password to the provided password
        admin.password_hash = ph.hash(admin_password)
        session.add(admin)
        session.commit()
        print("✅ Admin password reset successfully")
        print(f"   Username: admin")
    else:
        # Create admin user if doesn't exist
        admin = User(
            username="admin",
            password_hash=ph.hash(admin_password),
            is_admin=True,
        )
        session.add(admin)
        session.commit()
        print("✅ Admin user created successfully")
        print(f"   Username: admin")
