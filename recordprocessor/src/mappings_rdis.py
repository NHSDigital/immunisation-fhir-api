"""Mappings for converting vaccine type into target disease FHIR element"""


from elasticache import get_disease_mapping_json_from_cache


VACCINE_DISEASE_MAPPING2 = get_disease_mapping_json_from_cache()
