import logging
import redis
import os

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")


# get redis host from lambda environment variables
redis_host = os.environ.get('REDIS_HOST', 'redis')
redis_port = int(os.environ.get('REDIS_PORT', 6379))


def sync_handler(event, context):

    print("Marker23. New code - no publish @ 0935")
    logger.info("Marker23. New code - no publish @ 0936")

    # handler is triggered by S3 event
    logger.info("Event: %s", event)

    # Extract bucket and key from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    logger.info("Bucket: %s, Key: %s", bucket, key)

    # TEST REDIS code
    logger.info("Connecting to Redis at %s:%d", redis_host, redis_port)
    r = redis.Redis(host=redis_host, port=redis_port, db=0)
    try:
        with open(f"/tmp/{key}", 'rb') as file:
            data = file.read()
            r.set(key, data)
            logger.info("File %s stored in Redis", key)
    except Exception as e:
        logger.error("Error storing file in Redis: %s", e)
        raise
    finally:
        r.close()
    logger.info("Redis connection closed")
