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

from app.utils.admin_bootstrap import reset_admin

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

try:
    status = reset_admin(admin_password)
except ValueError as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)

print(f"✅ Admin account {status}")
print(f"   Username: admin")
