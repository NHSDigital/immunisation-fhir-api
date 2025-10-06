from constants import RedisCacheKey
from transform_configs import (
    transform_vaccine_map, transform_supplier_permissions, transform_validation_schema
)
from common.clients import logger
'''
Transform config file to format required in REDIS cache.
'''


def transform_map(data, file_type) -> dict:
    # Transform the vaccine map data as needed
    logger.info("Transforming data for file type: %s", file_type)
    if file_type == RedisCacheKey.PERMISSIONS_CONFIG_FILE_KEY:
        return transform_supplier_permissions(data)
    if file_type == RedisCacheKey.DISEASE_MAPPING_FILE_KEY:
        return transform_vaccine_map(data)
    if file_type == RedisCacheKey.VALIDATION_SCHEMA_FILE_KEY:
        return transform_validation_schema(data)

    logger.warning("No specific transformation defined for file type: %s", file_type)

    return data
