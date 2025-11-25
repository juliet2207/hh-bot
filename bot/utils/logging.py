import sys

from loguru import logger


def setup_logging():
    """Setup logging with colored output and custom format for the entire application"""
    from bot.config import settings  # Import here to avoid circular imports

    # Remove default logger
    logger.remove()

    # Define the format with timestamp and colored level
    format_string = "<green>{time:YYYY.MM.DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # Add colored handler
    logger.add(
        sys.stdout,
        format=format_string,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Add file handler for persistent logs
    logger.add(
        "logs/bot_{time:YYYY.MM.DD}.log",
        rotation="1 day",
        retention="7 days",
        level=settings.LOG_LEVEL,
        format="{time:YYYY.MM.DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        backtrace=True,
        diagnose=True,
    )

    return logger
    """Setup logging with colored output and custom format for the entire application"""
    # Remove default logger
    logger.remove()

    # Define the format with timestamp and colored level
    format_string = "<green>{time:YYYY.MM.DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # Add colored handler
    logger.add(
        sys.stdout,
        format=format_string,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Add file handler for persistent logs
    logger.add(
        "logs/bot_{time:YYYY.MM.DD}.log",
        rotation="1 day",
        retention="7 days",
        level=settings.LOG_LEVEL,
        format="{time:YYYY.MM.DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        backtrace=True,
        diagnose=True,
    )

    return logger


# Create a module-level logger instance
app_logger = setup_logging()


def get_logger(name: str = None):
    """
    Get a logger instance with the specified name
    """
    if name:
        return app_logger.bind(name=name)
    return app_logger


# Convenience functions for different log levels
def log_debug(message: str, **kwargs):
    app_logger.debug(message, **kwargs)


def log_info(message: str, **kwargs):
    app_logger.info(message, **kwargs)


def log_success(message: str, **kwargs):
    app_logger.success(message, **kwargs)


def log_warning(message: str, **kwargs):
    app_logger.warning(message, **kwargs)


def log_error(message: str, **kwargs):
    app_logger.error(message, **kwargs)


def log_critical(message: str, **kwargs):
    app_logger.critical(message, **kwargs)


# Export the logger for direct use
__all__ = [
    "app_logger",
    "get_logger",
    "log_debug",
    "log_info",
    "log_success",
    "log_warning",
    "log_error",
    "log_critical",
    "setup_logging",
]
