import json
from clients import logger, redis_cacher
from redis_disease_mapping import DiseaseMapping

disease_vaccine_mapping = DiseaseMapping(redis_cacher)


def sync_handler(event, context):

    logger.info("Marker3. New code - no publish @ 0936")

    # handler is triggered by S3 event
    logger.info("Event: %s", json.dumps(event, indent=2))

    # save the disease mapping to Redis
    logger.info("Saving disease mapping to Redis (TEST).")
    disease_vaccine_mapping.put({"text": "hello world"})
    logger.info("Disease mapping saved to Redis.")
