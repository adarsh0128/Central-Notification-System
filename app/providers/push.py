import logging
from app.providers.base import BaseProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

class PushProvider(BaseProvider):
    async def send(self, target: str, content: str, subject: str | None = None) -> None:
        logger.info(
            f"Attempting to send Push notification to {target}",
            extra={"target": target}
        )
        await self._simulate_delivery(settings.PUSH_FAILURE_RATE, "PUSH")
        logger.info(
            f"Successfully sent Push notification to {target}",
            extra={"target": target}
        )
