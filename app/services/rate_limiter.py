import time
import uuid
from redis.asyncio import Redis
from app.core.config import settings

class RateLimitExceededError(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")

class RateLimiterService:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def check_rate_limit(self, user_id: str) -> None:
        """Enforces a sliding window rate limit using Redis Sorted Sets (ZSET).
        
        Raises RateLimitExceededError if the limit is exceeded.
        """
        now = time.time()
        key = f"rate_limit:{user_id}"
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        limit = settings.RATE_LIMIT_MAX_REQUESTS

        # Remove elements older than the window
        cutoff = now - window

        # We use a pipeline to ensure all operations run atomically and efficiently
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, "-inf", cutoff)
            pipe.zcard(key)
            # Fetch the oldest request score to compute exact retry after if needed
            pipe.zrange(key, 0, 0, withscores=True)
            results = await pipe.execute()

        current_count = results[1]
        oldest_items = results[2]

        if current_count >= limit:
            # Calculate how long to wait until the oldest request falls out of the window
            if oldest_items:
                oldest_time = float(oldest_items[0][1])
                retry_after = max(1, int((oldest_time + window) - now))
            else:
                retry_after = 1
            raise RateLimitExceededError(retry_after)

        # Add the current request to the window
        member = f"{now}:{uuid.uuid4()}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zadd(key, {member: now})
            pipe.expire(key, window)
            await pipe.execute()
