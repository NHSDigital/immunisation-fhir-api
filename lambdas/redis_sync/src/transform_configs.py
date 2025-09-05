from clients import logger


def transform_vaccine_map(mapping):
    # Transform the vaccine map data as needed
    logger.info("Transforming vaccine map data")
    logger.info("source data: %s", mapping)

    vacc_to_diseases = {
        entry["vacc_type"]: entry["diseases"]
        for entry in mapping
        if "vacc_type" in entry and "diseases" in entry
    }
    diseases_to_vacc = {
        ':'.join(sorted(disease['code'] for disease in entry['diseases'])): entry['vacc_type']
        for entry in mapping
        if "diseases" in entry and "vacc_type" in entry
    }

    return {
        "vacc_to_diseases": vacc_to_diseases,
        "diseases_to_vacc": diseases_to_vacc
    }


def transform_supplier_permissions(mapping):
    """
    Transform a supplier-permission
    """
    logger.info("Transforming supplier permissions data")
    logger.info("source data: %s", mapping)

    supplier_permissions = {
        entry["supplier"]: entry["permissions"]
        for entry in mapping
        if "supplier" in entry and "permissions" in entry
    }
    ods_code_to_supplier = {
        ods_code: entry["supplier"]
        for entry in mapping
        if "ods_codes" in entry and "supplier" in entry
        for ods_code in entry["ods_codes"]
    }

    return {
        "supplier_permissions": supplier_permissions,
        "ods_code_to_supplier": ods_code_to_supplier
    }
