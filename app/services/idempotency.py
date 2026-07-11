import json
from typing import Any
from redis.asyncio import Redis
from app.core.config import settings

class IdempotencyLockError(Exception):
    """Raised when a duplicate request is received while the first one is still processing."""
    pass

class IdempotencyPayloadConflictError(Exception):
    """Raised when the same idempotency key is submitted with a different request payload."""
    pass

class IdempotencyService:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    def _get_key(self, key: str) -> str:
        return f"idempotency:{key}"

    async def check_or_lock(self, key: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Checks the state of an idempotency key.
        
        - If key does not exist, sets a lock status with the payload and returns None.
        - If key exists and payload differs, raises IdempotencyPayloadConflictError.
        - If key exists and status is LOCK, raises IdempotencyLockError.
        - If key exists and status is DONE, returns the cached response dictionary.
        """
        redis_key = self._get_key(key)
        val = await self.redis.get(redis_key)

        if not val:
            # Key does not exist. Acquire lock and store payload
            lock_data = {
                "status": "LOCK",
                "payload": payload
            }
            # Set key with a 120s TTL to prevent permanent lockups if server crashes
            success = await self.redis.set(
                redis_key,
                json.dumps(lock_data),
                ex=120,
                nx=True
            )
            if not success:
                # Concurrent race condition (key set by another process just now)
                raise IdempotencyLockError("A request with this idempotency key is already in progress.")
            return None

        data = json.loads(val)
        stored_payload = data.get("payload")

        # Check payload mismatch to raise a 409 conflict per specification
        if stored_payload != payload:
            raise IdempotencyPayloadConflictError(
                "The idempotency key is already associated with a different payload."
            )

        if data.get("status") == "LOCK":
            raise IdempotencyLockError(
                "A request with this idempotency key is already in progress."
            )

        # Return cached response (DONE status)
        return data

    async def save_response(self, key: str, payload: dict[str, Any], status_code: int, response_body: dict[str, Any]) -> None:
        """Stores the final response for the idempotency key and updates status to DONE."""
        redis_key = self._get_key(key)
        data = {
            "status": "DONE",
            "payload": payload,
            "status_code": status_code,
            "body": response_body
        }
        await self.redis.set(
            redis_key,
            json.dumps(data),
            ex=settings.IDEMPOTENCY_TTL_SECONDS
        )

    async def delete_key(self, key: str) -> None:
        """Deletes the idempotency key, allowing retry if the operation failed before completion."""
        redis_key = self._get_key(key)
        await self.redis.delete(redis_key)
