#!/usr/bin/env python3
"""
Check database tables
"""
import asyncio
from src.database import async_session
from sqlalchemy import text

async def check():
    async with async_session() as db:
        result = await db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = result.fetchall()
        print("Tables:", [t[0] for t in tables])

if __name__ == "__main__":
    asyncio.run(check())