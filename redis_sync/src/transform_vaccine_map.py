from clients import logger

import json


def transform_vaccine_map(data):
    # Transform the vaccine map data as needed
    logger.info("Transforming vaccine map data")
    logger.info("source data:%s", data)
    vaccines = data["vaccine"]
    diseases = data["disease"]

    # vaccines has a 1 to many with disease. Disease needs to have a reciprocal relationship
    for vaccine_id, vaccine_data in vaccines.items():
        for disease_id in vaccine_data["diseases"]:
            if "vaccines" not in diseases[disease_id]:
                diseases[disease_id]["vaccines"] = []
            diseases[disease_id]["vaccines"].append(vaccine_id)

    transformed_data = {
        "vaccine": vaccines,
        "disease": diseases
    }
    logger.info("transformed_data: %s", json.dumps(transformed_data))
    return transformed_data
