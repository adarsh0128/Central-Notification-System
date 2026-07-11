import pytest
from app.core.config import settings
from app.services.rate_limiter import RateLimiterService, RateLimitExceededError

@pytest.mark.asyncio
async def test_rate_limiter_allows_requests_below_threshold(test_redis) -> None:
    # Set limit temporarily to 3 for this test
    original_limit = settings.RATE_LIMIT_MAX_REQUESTS
    settings.RATE_LIMIT_MAX_REQUESTS = 3
    try:
        service = RateLimiterService(test_redis)
        user_id = "test_user_under_limit"

        # These 3 should succeed
        await service.check_rate_limit(user_id)
        await service.check_rate_limit(user_id)
        await service.check_rate_limit(user_id)
    finally:
        settings.RATE_LIMIT_MAX_REQUESTS = original_limit

@pytest.mark.asyncio
async def test_rate_limiter_blocks_exceeding_requests(test_redis) -> None:
    original_limit = settings.RATE_LIMIT_MAX_REQUESTS
    settings.RATE_LIMIT_MAX_REQUESTS = 2
    try:
        service = RateLimiterService(test_redis)
        user_id = "test_user_over_limit"

        await service.check_rate_limit(user_id)
        await service.check_rate_limit(user_id)

        # 3rd request must fail
        with pytest.raises(RateLimitExceededError) as exc_info:
            await service.check_rate_limit(user_id)

        assert exc_info.value.retry_after > 0
        assert "Rate limit exceeded" in str(exc_info.value)
    finally:
        settings.RATE_LIMIT_MAX_REQUESTS = original_limit
