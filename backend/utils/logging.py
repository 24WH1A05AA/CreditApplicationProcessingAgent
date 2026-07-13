import logging
import sys
from backend.config import settings

def setup_logging():
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure formatter
    log_format = (
        "[%(asctime)s] %(levelname)s in %(module)s (%(filename)s:%(lineno)d): %(message)s"
    )
    
    # Clear existing handlers
    logging.root.handlers = []
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Get logger for application
    logger = logging.getLogger(settings.APP_NAME)
    logger.info("Logging initialized with level: %s", settings.LOG_LEVEL)
    return logger

# Single instance of application logger
logger = setup_logging()
