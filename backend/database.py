import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Run lightweight migrations for schema changes that create_all won't handle.
    # These are idempotent — safe to run on every startup.
    migrations = [
        "ALTER TABLE simulations ALTER COLUMN user_id DROP NOT NULL;",
        "ALTER TABLE personas ALTER COLUMN created_by DROP NOT NULL;",
    ]
    async with engine.begin() as conn:
        for sql in migrations:
            try:
                await conn.execute(text(sql))
                logger.info(f"Migration OK: {sql}")
            except Exception as e:
                # Column might already be nullable, or table might not exist yet
                logger.warning(f"Migration skipped: {sql} — {e}")
