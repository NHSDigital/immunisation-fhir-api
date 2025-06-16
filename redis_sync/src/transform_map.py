from constants import RedisCacheKey
from transform_vaccine_map import transform_vaccine_map
'''

'''


def transform_map(data, file_type):
    # Transform the vaccine map data as needed

    if file_type == RedisCacheKey.DISEASE_VACCINE_FILENAME:
        return transform_vaccine_map(data)
    if file_type == RedisCacheKey.DISEASE_MAPPING_FILE_KEY:
        return data  # No transformation available yet
    return data  # Default case, return data as is if no transformation is defined
