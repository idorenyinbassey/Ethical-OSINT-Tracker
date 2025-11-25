#!/usr/bin/env python
"""Reset admin user password"""
from argon2 import PasswordHasher
from app.db import init_db, get_session
from app.models.user import User
from sqlmodel import select

ph = PasswordHasher()

# Initialize database
init_db()

# Reset admin password
with get_session() as session:
    stmt = select(User).where(User.username == "admin")
    admin = session.exec(stmt).first()
    
    if admin:
        # Update password to "changeme"
        admin.password_hash = ph.hash("changeme")
        session.add(admin)
        session.commit()
        print("✅ Admin password reset to 'changeme'")
        print(f"   Username: admin")
        print(f"   Password: changeme")
    else:
        # Create admin user if doesn't exist
        admin = User(
            username="admin",
            password_hash=ph.hash("changeme"),
        )
        session.add(admin)
        session.commit()
        print("✅ Admin user created")
        print(f"   Username: admin")
        print(f"   Password: changeme")
