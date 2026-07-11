from typing import AsyncGenerator
from redis.asyncio import Redis
from app.core.config import settings

# Shared Redis client using a connection pool
redis_client: Redis = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,  # Automatically decode bytes to str
    max_connections=50,     # Connection pool sizing
)

async def get_redis() -> AsyncGenerator[Redis, None]:
    """Dependency injection provider for Redis clients."""
    yield redis_client

async def close_redis() -> None:
    """Explicit cleanup function to close Redis connection pool."""
    await redis_client.aclose()
