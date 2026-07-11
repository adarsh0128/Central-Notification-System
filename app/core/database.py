from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

# Initialize Async Engine with optimized connection pool settings
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,          # Standard pool size
    max_overflow=10,       # Allow surge connections
    pool_recycle=1800,     # Recycle connection every 30 mins
    pool_pre_ping=True,    # Liveness check before using connection
    echo=False,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to provide an async DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
