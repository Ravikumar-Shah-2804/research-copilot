#!/usr/bin/env python3
"""
Script to verify admin user exists with correct credentials
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import select
from src.database import async_session
from src.models.user import User
try:
    import bcrypt
    def verify_password(plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
except ImportError:
    from src.services.auth import verify_password

async def verify_admin_user():
    """Verify admin user exists and password matches 'admin123'"""
    try:
        async with async_session() as session:
            # Query for admin user (assuming username is 'admin')
            result = await session.execute(
                select(User).where(User.username == 'admin')
            )
            user = result.scalar_one_or_none()

            if not user:
                print("❌ Admin user not found in database")
                return False

            print(f"✅ Admin user found: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Active: {user.is_active}")
            print(f"   Superuser: {user.is_superuser}")

            # Verify password
            if verify_password('admin123', user.hashed_password):
                print("✅ Password verification successful")
                return True
            else:
                print("❌ Password verification failed")
                return False

    except Exception as e:
        print(f"❌ Error verifying admin user: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_admin_user())
    sys.exit(0 if success else 1)