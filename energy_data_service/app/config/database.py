import logging
from collections.abc import AsyncGenerator

from app.config.settings import DatabaseConfig, Settings
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

log = logging.getLogger(__name__)


class Database:
    """Database configuration for the application."""

    def __init__(self, config: Settings):
        self.config = config
        self.engine = self.create_database_engine()
        self.session_factory = self.create_session_factory()

    def create_database_engine(self) -> AsyncEngine:
        """Create and return an asynchronous database engine."""
        return create_async_engine(self.config.database.url, echo=self.config.debug)

    def create_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Create and return an asynchronous session factory."""
        return async_sessionmaker(self.engine, expire_on_commit=False)

    async def get_database_session(self) -> AsyncGenerator[AsyncSession]:
        """Get a database session generator."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
