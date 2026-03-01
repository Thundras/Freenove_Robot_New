import logging

logger = logging.getLogger(__name__)

def initialize(context):
    """
    Example Plugin: Just logs a message.
    context could be the main Robot object.
    """
    logger.info("Hello from Example Plugin! Robot is ready.")
