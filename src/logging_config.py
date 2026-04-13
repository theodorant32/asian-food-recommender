"""Logging configuration."""

import sys
from pathlib import Path
from loguru import logger


def setup_logging(log_level: str = "INFO", log_file: str = "./logs/app.log", retention_days: int = 7) -> None:
    logger.remove()

    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} | {message}",
        rotation="10 MB",
        retention=f"{retention_days} days",
        compression="zip",
        enqueue=True,
    )

    logger.info(f"Logging configured: level={log_level}, file={log_file}")
