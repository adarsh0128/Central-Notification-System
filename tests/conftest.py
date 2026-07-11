import asyncio
import pytest
from typing import AsyncGenerator, Any
from httpx import AsyncClient, ASGITransport
from redis.asyncio import Redis, from_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.main import app
from app.models import Base

# Test database URL targeting the postgres container on port 5433
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/notification_db", "/notification_test_db")

@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> None:
    """Session-scoped setup to create the test database once before any tests run."""
    import asyncpg
    
    async def _create_db() -> None:
        try:
            # Connect to default postgres DB
            conn = await asyncpg.connect(
                user="postgres",
                password="postgrespassword",
                host="localhost",
                port=5433,
                database="postgres"
            )
            # Terminate active connections to test DB
            await conn.execute(
                """
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = 'notification_test_db'
                  AND pid <> pg_backend_pid();
                """
            )
            await conn.execute("DROP DATABASE IF EXISTS notification_test_db")
            await conn.execute("CREATE DATABASE notification_test_db")
            await conn.close()
        except Exception as e:
            print(f"Warning: Failed to recreate test database: {e}")

    # Run DB creation in a temporary event loop before the test session starts
    asyncio.run(_create_db())

@pytest.fixture
async def test_engine() -> AsyncGenerator[Any, None]:
    """Function-scoped database engine. Ensures tables exist."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    
    await engine.dispose()

@pytest.fixture
async def db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provides a transactional database session per test.
    
    Rolls back transaction at the end of the test to keep tests isolated and fast.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()

    AsyncSessionLocal = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    session = AsyncSessionLocal()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()

@pytest.fixture
async def test_redis() -> AsyncGenerator[Redis, None]:
    """Provides a clean Redis connection per test."""
    redis = from_url(settings.REDIS_URL, decode_responses=True)
    await redis.flushdb()  # Ensure cache/lock isolation
    yield redis
    await redis.aclose()

@pytest.fixture
async def client(db, test_redis) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI AsyncClient configured with mock DB and Redis dependency overrides."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: test_redis

    # httpx 0.28+ requires ASGI transport wrapper explicitly
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
