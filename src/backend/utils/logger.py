"""
Logging Configuration for QUANTUM TRADER V1
Structured logging with JSON output and file rotation
"""

import logging
import sys
import json
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
import datetime


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add additional fields if present
        if hasattr(record, "service"):
            log_data["service"] = record.service

        if hasattr(record, "component"):
            log_data["component"] = record.component

        if hasattr(record, "exchange"):
            log_data["exchange"] = record.exchange

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            log_data["stack_trace"] = record.stack_info

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        log_color = self.COLORS.get(record.levelname, self.RESET)
        levelname = f"{log_color}{record.levelname}{self.RESET}"
        return f"{levelname}: {record.getMessage()}"


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    json_logging: bool = False
):
    """
    Setup logging configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        json_logging: Whether to use JSON format
    """
    if log_dir is None:
        from src.backend.utils.config import Config
        log_dir = Config().settings.log_dir

    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if json_logging:
        console_formatter = JSONFormatter()
    else:
        console_formatter = ColoredFormatter()

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    log_file = log_dir / "quantum_trader.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(numeric_level)

    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Error log file (separate)
    error_file = log_dir / "quantum_trader_error.log"
    error_handler = RotatingFileHandler(
        error_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)

    # Add custom attributes to log records
    class ServiceFilter(logging.Filter):
        def filter(self, record):
            if hasattr(record, "service"):
                record.service = record.service
            if hasattr(record, "component"):
                record.component = record.component
            if hasattr(record, "exchange"):
                record.exchange = record.exchange
            return True

    root_logger.addFilter(ServiceFilter())

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


def log_service_event(
    service_name: str,
    event_type: str,
    message: str,
    level: str = "INFO",
    **kwargs
):
    """Log a structured service event"""
    logger = get_logger(f"{service_name}.{event_type}")
    extra = {"service": service_name, **kwargs}
    getattr(logger, level.lower())(message, extra=extra)


def log_trade_event(
    position_id: str,
    event_type: str,
    message: str,
    **kwargs
):
    """Log a trade-related event"""
    logger = get_logger(f"trades.{event_type}")
    extra = {"position_id": position_id, **kwargs}
    getattr(logger, level.lower())(message, extra=extra)


def log_error_with_context(error: Exception, context: dict):
    """Log an error with additional context"""
    logger = get_logger(__name__)
    logger.error(
        f"{str(error)}",
        exc_info=True,
        extra={"context": context}
    )