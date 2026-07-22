"""Application log-file configuration."""

import logging
from logging.handlers import RotatingFileHandler

from .storage_paths import get_persistent_app_dir


LOG_DIR = get_persistent_app_dir() / "logs"
LOG_FILE = LOG_DIR / "g2b_alert.log"


def setup_logger(name="g2b_alert"):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
