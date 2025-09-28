import asyncio
from backend.src.database import get_db
from sqlalchemy import text

async def alter_table():
    async for session in get_db():
        await session.execute(text('ALTER TABLE research_papers ALTER COLUMN published_date TYPE TIMESTAMP WITH TIME ZONE'))
        await session.execute(text('ALTER TABLE research_papers ALTER COLUMN pdf_processing_date TYPE TIMESTAMP WITH TIME ZONE'))
        await session.execute(text('ALTER TABLE research_papers ALTER COLUMN submission_date TYPE TIMESTAMP WITH TIME ZONE'))
        await session.execute(text('ALTER TABLE research_papers ALTER COLUMN update_date TYPE TIMESTAMP WITH TIME ZONE'))
        await session.execute(text('ALTER TABLE research_papers ALTER COLUMN last_ingestion_attempt TYPE TIMESTAMP WITH TIME ZONE'))
        await session.execute(text('ALTER TABLE research_papers ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE'))
        await session.execute(text('ALTER TABLE research_papers ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE'))
        await session.commit()
        break

if __name__ == "__main__":
    asyncio.run(alter_table())