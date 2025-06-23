from constants import RedisCacheKey
from clients import logger
from src.transform_configs import transform_vaccine_map, transform_supplier_permissions
'''
Transform config file to format required in REDIS cache.
'''


def transform_map(data, file_type):
    # Transform the vaccine map data as needed
    logger.info("Transforming data for file type: %s", file_type)
    if file_type == RedisCacheKey.PERMISSIONS_CONFIG_FILE_KEY:
        return transform_supplier_permissions(data)
    if file_type == RedisCacheKey.DISEASE_MAPPING_FILE_KEY:
        return transform_vaccine_map(data)
    logger.info("No specific transformation defined for file type: %s", file_type)
    return data  # Default case, return data as is if no transformation is defined
