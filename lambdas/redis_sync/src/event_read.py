import redis


# Reads a Redis hash using the 'read' key from the event payload.
def read_event(redis_client: redis.Redis, event: dict, logger) -> dict:
    try:
        read_key = event["read"]
        if not read_key:
            return {"status": "error", "message": "Read key is required."}
        return redis_client.hgetall(read_key)

    except Exception:
        msg = f"Error reading key '{read_key}' from Redis cache"
        logger.exception(msg)
        return {"status": "error", "message": msg}
