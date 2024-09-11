"""
Logging configuration module with automatic log rotation.

This module defines the setup_logging() function, which configures the logging system
using TimedRotatingFileHandler. Logs are written to the 'app.log' file
and rotated daily at midnight. Logs from the last 3 days are retained.
"""

import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import time

def setup_logging():
    """
    Configures the logging system with automatic log rotation.

    This function creates and configures a logger that writes logs to the 'app.log' file.
    Logs are rotated daily at midnight, and logs from the last 3 days are retained.

    Usage:
    - Import this function in your script
    - Call it at the beginning of your script
    - Use logging.getLogger(__name__) to create loggers in your modules

    Returns:
        None
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = TimedRotatingFileHandler(
        filename='app.log',
        when='midnight',
        interval=1,
        backupCount=3,
        atTime=time(0,0),
        encoding='utf-8'

    )

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)
