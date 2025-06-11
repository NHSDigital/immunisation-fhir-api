import logging

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")
    

def sync_handler(event, context):
    print("Marker23. New code - no publish @ 0935")
    logger.info("Marker23. New code - no publish @ 0936")
