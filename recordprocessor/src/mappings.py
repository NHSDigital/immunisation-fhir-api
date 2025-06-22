"""Mappings for converting vaccine type into target disease FHIR element"""
import json
from constants import Urls
from src.clients import redis_client


def map_target_disease(vaccine: str) -> list:
    """Returns the target disease element for the given vaccine type using the vaccine_disease_mapping"""
    diseases_str = redis_client.hget("vacc-to-diseases", vaccine)
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
