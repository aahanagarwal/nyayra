"""Async engine/session setup for SQLite via aiosqlite."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.models import Base

_settings = get_settings()

engine = create_async_engine(_settings.database_url, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an AsyncSession."""
    async with async_session_maker() as session:
        yield session


async def init_db() -> None:
    """Create all tables. Safe to call repeatedly (no-op on existing tables)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
