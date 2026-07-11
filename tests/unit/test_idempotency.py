import pytest
from app.services.idempotency import (
    IdempotencyService,
    IdempotencyLockError,
    IdempotencyPayloadConflictError,
)

@pytest.mark.asyncio
async def test_idempotency_workflow_success(test_redis) -> None:
    service = IdempotencyService(test_redis)
    key = "idemp_test_key"
    payload = {"userId": "user1", "templateName": "welcome", "variables": {}}

    # 1. Lock on first request
    cached_res = await service.check_or_lock(key, payload)
    assert cached_res is None

    # 2. Re-submitting same payload while lock is active should raise LockError
    with pytest.raises(IdempotencyLockError):
        await service.check_or_lock(key, payload)

    # 3. Complete processing and save response
    response_body = {"id": "notification-uuid-123", "status": "PENDING"}
    await service.save_response(key, payload, status_code=201, response_body=response_body)

    # 4. Requesting again with the same key and payload should return the cached response
    cached_res = await service.check_or_lock(key, payload)
    assert cached_res is not None
    assert cached_res["status"] == "DONE"
    assert cached_res["status_code"] == 201
    assert cached_res["body"] == response_body

@pytest.mark.asyncio
async def test_idempotency_payload_conflict(test_redis) -> None:
    service = IdempotencyService(test_redis)
    key = "idemp_conflict_key"
    payload_1 = {"userId": "user1", "templateName": "welcome"}
    payload_2 = {"userId": "user2", "templateName": "welcome"}

    # Lock on first payload
    await service.check_or_lock(key, payload_1)

    # Re-submitting with a different payload should raise conflict error
    with pytest.raises(IdempotencyPayloadConflictError):
        await service.check_or_lock(key, payload_2)

@pytest.mark.asyncio
async def test_idempotency_delete_key_allows_retry(test_redis) -> None:
    service = IdempotencyService(test_redis)
    key = "idemp_delete_key"
    payload = {"userId": "user1"}

    # Lock
    await service.check_or_lock(key, payload)

    # Delete (e.g. after internal server failure)
    await service.delete_key(key)

    # Should lock successfully again
    cached_res = await service.check_or_lock(key, payload)
    assert cached_res is None
