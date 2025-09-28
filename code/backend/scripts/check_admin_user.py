#!/usr/bin/env python3
"""
Script to check if default admin user exists and create if not
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from src.config import settings
from src.database import async_session, engine
from src.models.user import User
from src.services.auth import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_users_table():
    """Add missing columns to users table"""
    async with engine.begin() as conn:
        # Add missing columns
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id)"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS login_attempts INTEGER DEFAULT 0"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP WITH TIME ZONE"))
        logger.info("Users table migration completed")

async def check_and_create_admin_user():
    """Check if admin user exists, create if not"""
    # First migrate the table
    await migrate_users_table()

    async with async_session() as session:
        try:
            # Check if admin user exists
            result = await session.execute(
                select(User).where(User.username == "admin")
            )
            admin_user = result.scalar_one_or_none()

            if admin_user:
                logger.info("Admin user already exists")
                return

            # Create admin user
            hashed_password = get_password_hash("admin123")
            new_admin = User(
                username="admin",
                email="admin@researchcopilot.com",
                hashed_password=hashed_password,
                full_name="Administrator",
                is_active=True,
                is_superuser=True
            )

            session.add(new_admin)
            await session.commit()
            await session.refresh(new_admin)

            logger.info(f"Created admin user with ID: {new_admin.id}")

        except Exception as e:
            logger.error(f"Error checking/creating admin user: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(check_and_create_admin_user())