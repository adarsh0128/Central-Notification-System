import logging
from app.providers.base import BaseProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailProvider(BaseProvider):
    async def send(self, target: str, content: str, subject: str | None = None) -> None:
        logger.info(
            f"Attempting to send email to {target}",
            extra={"target": target, "subject": subject}
        )
        await self._simulate_delivery(settings.EMAIL_FAILURE_RATE, "EMAIL")
        logger.info(
            f"Successfully sent email to {target}",
            extra={"target": target, "subject": subject}
        )
