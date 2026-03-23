"""
Structured logging configuration for the Water Utility Chatbot.

This module provides centralized logging with:
- Structured log format (JSON-compatible)
- Separate handlers for different log levels
- Sensitive data filtering
- Request/response tracking
"""

import logging
import logging.handlers
from pathlib import Path
import json
from typing import Any, Dict

# Create logs directory
LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Sensitive fields to redact
SENSITIVE_FIELDS = {"api_key", "token", "password", "secret", "phone", "account_number"}


class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive information from logs."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive fields from log records."""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            for field in SENSITIVE_FIELDS:
                if field in record.msg.lower():
                    record.msg = record.msg.replace(record.msg, "[REDACTED]")
        return True


class StructuredFormatter(logging.Formatter):
    """Format logs as structured JSON for easier parsing."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Configure logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("water_utility_bot")
    logger.setLevel(getattr(logging, level))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    structured_formatter = StructuredFormatter()
    simple_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(structured_formatter)
    file_handler.addFilter(SensitiveDataFilter())
    
    # File handler for errors only
    error_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "errors.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(structured_formatter)
    error_handler.addFilter(SensitiveDataFilter())
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    console_handler.addFilter(SensitiveDataFilter())
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    Log a message with additional context data.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context data to include
    """
    record = logging.LogRecord(
        name=logger.name,
        level=getattr(logging, level.upper()),
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    record.extra_data = context
    getattr(logger, level.lower())(message, extra={"extra_data": context})


# Initialize logger
logger = setup_logging()
