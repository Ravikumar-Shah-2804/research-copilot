import asyncio
import sys
sys.path.insert(0, 'src')

from sqlalchemy import text
from src.database import engine

async def alter():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE users ALTER COLUMN full_name DROP NOT NULL;"))
        print("Altered")

asyncio.run(alter())