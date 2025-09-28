#!/usr/bin/env python3
"""
Script to update admin user's password to 'admin123'
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import select, update
from src.database import async_session
from src.models.user import User
from src.services.auth import get_password_hash

async def update_admin_password():
    """Update admin user password to 'admin123'"""
    try:
        # Generate bcrypt hash for 'admin123'
        new_password_hash = get_password_hash('admin123')
        print(f"Generated bcrypt hash: {new_password_hash}")

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
            print(f"   Current hashed password: {user.hashed_password}")

            # Update password
            await session.execute(
                update(User).where(User.id == user.id).values(hashed_password=new_password_hash)
            )
            await session.commit()

            print("✅ Admin user password updated successfully")
            print(f"   New hashed password: {new_password_hash}")
            return True

    except Exception as e:
        print(f"❌ Error updating admin password: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(update_admin_password())
    sys.exit(0 if success else 1)