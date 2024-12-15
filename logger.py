# logger.py

import logging

# Configure logging
logging.basicConfig(
    filename='app.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger()

def log_info(message):
    """Log an informational message."""
    logger.info(message)

def log_error(message, error):
    """Log an error message with exception details."""
    logger.error(f"{message}: {error}", exc_info=True)
