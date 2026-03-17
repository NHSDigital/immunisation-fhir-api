from common.clients import logger
from common.models.constants import RedisHashKeys


def transform_vaccine_map(mapping):
    # Transform the vaccine map data as needed
    logger.info("Transforming vaccine map data")
    logger.info("source data: %s", mapping)

    vacc_to_diseases = {
        entry["vacc_type"]: entry["diseases"] for entry in mapping if "vacc_type" in entry and "diseases" in entry
    }
    diseases_to_vacc = {
        ":".join(sorted(disease["code"] for disease in entry["diseases"])): entry["vacc_type"]
        for entry in mapping
        if "diseases" in entry and "vacc_type" in entry
    }

    all_disease_codes = set()
    target_disease_to_vaccs = {}
    for entry in mapping:
        if "vacc_type" not in entry or "diseases" not in entry:
            continue
        vacc_type = entry["vacc_type"]
        for disease in entry["diseases"]:
            code = disease["code"]
            all_disease_codes.add(code)
            if code not in target_disease_to_vaccs:
                target_disease_to_vaccs[code] = []
            target_disease_to_vaccs[code].append(vacc_type)

    target_disease_list = {"codes": sorted(all_disease_codes)}
    target_disease_to_vaccs_serialized = {code: sorted(vaccs) for code, vaccs in target_disease_to_vaccs.items()}

    return {
        RedisHashKeys.VACCINE_TYPE_TO_DISEASES_HASH_KEY: vacc_to_diseases,
        RedisHashKeys.DISEASES_TO_VACCINE_TYPE_HASH_KEY: diseases_to_vacc,
        RedisHashKeys.TARGET_DISEASE_LIST_KEY: target_disease_list,
        RedisHashKeys.TARGET_DISEASE_TO_VACCS_KEY: target_disease_to_vaccs_serialized,
    }


def transform_supplier_permissions(mapping):
    """
    Transform a supplier-permission
    """
    logger.info("Transforming supplier permissions data")
    logger.info("source data: %s", mapping)

    supplier_permissions = {
        entry["supplier"]: entry["permissions"] for entry in mapping if "supplier" in entry and "permissions" in entry
    }
    ods_code_to_supplier = {
        ods_code: entry["supplier"]
        for entry in mapping
        if "ods_codes" in entry and "supplier" in entry
        for ods_code in entry["ods_codes"]
    }

    return {
        "supplier_permissions": supplier_permissions,
        "ods_code_to_supplier": ods_code_to_supplier,
    }
