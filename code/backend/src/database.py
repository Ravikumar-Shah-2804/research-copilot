"""
Database configuration and connection management
"""
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from .config import settings

logger = logging.getLogger(__name__)

# Async engine
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
)

# Async session factory
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all database tables"""
    try:
        async with engine.begin() as conn:
            # Create tables
            await conn.run_sync(Base.metadata.create_all)

            # Verify connection
            result = await conn.execute(text("SELECT 1"))
            logger.info("Database connection verified")

    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


async def check_database_health() -> bool:
    """Check database health"""
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False