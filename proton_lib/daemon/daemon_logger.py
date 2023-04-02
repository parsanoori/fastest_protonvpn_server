import logging
import os
from logging.handlers import RotatingFileHandler

from ..constants import PROTON_XDG_CACHE_HOME_LOGS
import time


def get_logger():
    """Create the logger."""
    FORMATTER = logging.Formatter(
        "%(asctime)s — %(filename)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s" # noqa
    )
    FORMATTER.converter = time.gmtime

    if not os.path.isdir(PROTON_XDG_CACHE_HOME_LOGS):
        os.makedirs(PROTON_XDG_CACHE_HOME_LOGS)

    LOGFILE = os.path.join(PROTON_XDG_CACHE_HOME_LOGS, "protonvpn-daemon.log")

    logger = logging.getLogger("protonvpn-daemon-logger")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(FORMATTER)

    logging_level = logging.INFO

    logger.setLevel(logging_level)
    # Starts a new file at 3MB size limit
    file_handler = RotatingFileHandler(
        LOGFILE, maxBytes=3145728, backupCount=3
    )
    file_handler.setFormatter(FORMATTER)
    logger.addHandler(file_handler)

    return logger


logger = get_logger()
