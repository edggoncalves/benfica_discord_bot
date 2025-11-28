"""Structured logging configuration for better log analysis."""

import json
import logging
from datetime import UTC, datetime


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Formats log records as JSON for easier parsing with tools like jq, grep,
    or log aggregators. Useful for production environments where logs need
    to be analyzed programmatically.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format.

        Returns:
            JSON-formatted log string.
        """
        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "channel_id"):
            log_data["channel_id"] = record.channel_id
        if hasattr(record, "command"):
            log_data["command"] = record.command

        return json.dumps(log_data)
