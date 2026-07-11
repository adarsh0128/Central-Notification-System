import json
import logging
from contextvars import ContextVar
from typing import Any

# Async/Thread-safe context variables for trace context
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")
notification_id_ctx: ContextVar[str] = ContextVar("notification_id", default="")
channel_ctx: ContextVar[str] = ContextVar("channel", default="")
status_ctx: ContextVar[str] = ContextVar("status", default="")

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Handle exceptions
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Inject context variables if set
        if req_id := request_id_ctx.get():
            log_data["request_id"] = req_id
        if usr_id := user_id_ctx.get():
            log_data["user_id"] = usr_id
        if notif_id := notification_id_ctx.get():
            log_data["notification_id"] = notif_id
        if chan := channel_ctx.get():
            log_data["channel"] = chan
        if stat := status_ctx.get():
            log_data["status"] = stat

        # Inject other custom fields passed via extra=
        for key, val in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                "msg", "name", "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName"
            }:
                log_data[key] = val

        return json.dumps(log_data)

def setup_logging() -> None:
    from app.core.config import settings
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL.upper())
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Minimize noise from third-party libraries if in production
    if settings.ENVIRONMENT != "dev":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
