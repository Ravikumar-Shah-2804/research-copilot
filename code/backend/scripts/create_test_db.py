#!/usr/bin/env python3
"""
Script to create the test database for e2e tests.
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def create_test_database():
    """Create the test database if it doesn't exist."""
    # Connect to postgres database to create the test database
    admin_engine = create_async_engine(
        "postgresql+asyncpg://postgres:root@localhost:5432/postgres",
        echo=True,
        isolation_level="AUTOCOMMIT"  # Required for CREATE DATABASE
    )

    try:
        async with admin_engine.connect() as conn:
            # Create test database if it doesn't exist
            await conn.execute(text("CREATE DATABASE research_copilot_test"))
            print("Created test database: research_copilot_test")
    except Exception as e:
        if "already exists" in str(e):
            print("Test database already exists: research_copilot_test")
        else:
            print(f"Error creating test database: {e}")
            raise
    finally:
        await admin_engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_test_database())