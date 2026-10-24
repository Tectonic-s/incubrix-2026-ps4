"""Structured JSON Logger with sensitive token masking."""
import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variables for request tracking
current_correlation_id: ContextVar[Optional[str]] = ContextVar("current_correlation_id", default=None)
current_job_id: ContextVar[Optional[str]] = ContextVar("current_job_id", default=None)

# Patterns to mask sensitive data
SECRET_PATTERNS = [
    re.compile(r'(api[-_]?key|token|secret|password|authorization)["\']?\s*[:=]\s*["\']?([^"\'\s,}{]+)', re.IGNORECASE),
    re.compile(r'Bearer\s+([A-Za-z0-9_\-\.]+)', re.IGNORECASE),
]


def mask_secrets(text: str) -> str:
    """Mask tokens and secrets in strings so they never appear in logs."""
    if not isinstance(text, str):
        return text
    masked = text
    for pattern in SECRET_PATTERNS:
        def repl(match):
            full_match = match.group(0)
            secret_part = match.group(match.lastindex)
            if len(secret_part) > 6:
                redacted = secret_part[:2] + "****" + secret_part[-2:]
            else:
                redacted = "****"
            return full_match.replace(secret_part, redacted)
        masked = pattern.sub(repl, masked)
    return masked


class JSONFormatter(logging.Formatter):
    """Format log records as structured JSON."""
    def format(self, record: logging.LogRecord) -> str:
        # Resolve context variables
        corr_id = getattr(record, "correlation_id", None) or current_correlation_id.get() or "none"
        job_id = getattr(record, "job_id", None) or current_job_id.get() or "none"

        raw_message = record.getMessage()
        masked_message = mask_secrets(raw_message)

        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": masked_message,
            "job_id": job_id,
            "correlation_id": corr_id,
        }

        # Include extra payload if provided
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            # Mask any secrets inside extra_data
            clean_extra = json.loads(mask_secrets(json.dumps(record.extra_data)))
            log_data["data"] = clean_extra

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def get_logger(name: str = "incubrix") -> logging.Logger:
    """Configures and returns a structured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


logger = get_logger("incubrix.service")
