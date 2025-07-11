from clients import logger


def transform_vaccine_map(map):
    # Transform the vaccine map data as needed
    logger.info("Transforming vaccine map data")
    logger.info("source data:%s", map)

    vacc_to_diseases = {m['vacc_type']: m['diseases'] for m in map}
    diseases_to_vacc = {':'.join(sorted(d['code'] for d in m['diseases'])): m['vacc_type'] for m in map}

    return {
        "vacc_to_diseases": vacc_to_diseases,
        "diseases_to_vacc": diseases_to_vacc
    }


def transform_supplier_permissions(supplier):
    """
    Transform a supplier-permission
    """
    logger.info("Transforming supplier permissions data")
    logger.info("source data: %s", supplier)

    supplier_permissions = {
        entry["supplier"]: entry["permissions"] for entry in supplier
    }

    return {"supplier_permissions": supplier_permissions}
