import logging
from app.providers.base import BaseProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

class SMSProvider(BaseProvider):
    async def send(self, target: str, content: str, subject: str | None = None) -> None:
        logger.info(
            f"Attempting to send SMS to {target}",
            extra={"target": target}
        )
        await self._simulate_delivery(settings.SMS_FAILURE_RATE, "SMS")
        logger.info(
            f"Successfully sent SMS to {target}",
            extra={"target": target}
        )
