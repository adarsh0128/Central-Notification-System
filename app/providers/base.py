import abc
import asyncio
import random
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class ProviderError(Exception):
    """Custom exception raised when a mock provider fails to deliver."""
    pass

class BaseProvider(abc.ABC):
    @abc.abstractmethod
    async def send(self, target: str, content: str, subject: str | None = None) -> None:
        """Sends a notification to the target. Should raise ProviderError if failed."""
        pass

    async def _simulate_delivery(self, failure_rate: float, channel_name: str) -> None:
        """Simulates latency and failure rate for mock delivery."""
        # Calculate random latency in the configured range
        min_lat = settings.PROVIDER_MIN_LATENCY_MS
        max_lat = settings.PROVIDER_MAX_LATENCY_MS
        latency = random.randint(min_lat, max_lat) / 1000.0
        
        await asyncio.sleep(latency)

        # Simulate random failure
        if random.random() < failure_rate:
            logger.warning(
                f"Simulating delivery failure on {channel_name} channel",
                extra={"failure_rate": failure_rate, "latency_seconds": latency}
            )
            raise ProviderError(f"Temporary service disruption on {channel_name} mock provider.")
