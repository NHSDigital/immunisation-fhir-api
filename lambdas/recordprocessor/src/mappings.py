"""Mappings for converting vaccine type into target disease FHIR element"""

import json

from common.redis_client import get_redis_client
from constants import Urls


def map_target_disease(vaccine: str) -> list:
    """Returns the target disease element for the given vaccine type using the vaccine_disease_mapping"""
    diseases_str = get_redis_client().hget("vacc_to_diseases", vaccine)
    diseases = json.loads(diseases_str) if diseases_str else []
    return [
        {
            "coding": [
                {
                    "system": Urls.SNOMED,
                    "code": disease["code"],
                    "display": disease["term"],
                }
            ]
        }
        for disease in diseases
    ]
