import json
def convert_to_flat_json(resource_json, operation):
    flat_dict = {
        "NHS_NUMBER": resource_json.get("contained", [])[1].get("identifier", [])[0].get("value"),
        "PERSON_FORENAME": resource_json.get("contained", [])[1].get("name", [])[0].get("given"),
        "PERSON_SURNAME": resource_json.get("contained", [])[1].get("name", [])[0].get("family"),
        "PERSON_DOB": resource_json.get("contained", [])[1].get("birthDate"),
        "PERSON_GENDER_CODE": resource_json.get("contained", [])[1].get("gender"),
        "PERSON_POSTCODE": resource_json.get("contained", [])[1].get("address", [])[0].get("postalCode"),
        "DATE_AND_TIME": resource_json.get("occurrenceDateTime"),
        "SITE_CODE": resource_json.get("performer", [])[1].get("actor", {}).get("identifier", {}).get("value"),
        "SITE_CODE_TYPE_URI": resource_json.get("performer", [])[1].get("actor", {}).get("identifier", {}).get("system"),
        "UNIQUE_ID": resource_json.get("identifier", [])[0].get("value"),
        "UNIQUE_ID_URI": resource_json.get("identifier", [])[0].get("system"),
        "ACTION_FLAG": operation,
        "PERFORMING_PROFESSIONAL_FORENAME": resource_json.get("contained", [])[0].get("name", [])[0].get("given"),
        "PERFORMING_PROFESSIONAL_SURNAME": resource_json.get("contained", [])[0].get("name", [])[0].get("family"),
        "RECORDED_DATE": resource_json.get("recorded"),
        "PRIMARY_SOURCE": resource_json.get("primarySource"),
        "VACCINATION_PROCEDURE_CODE": resource_json.get("extension", [])[0].get("valueCodeableConcept", {}).get("coding", [])[0].get("code"),
        "VACCINATION_PROCEDURE_TERM": resource_json.get("extension", [])[0].get("valueCodeableConcept", {}).get("coding", [])[0].get("display"),
        "DOSE_SEQUENCE": resource_json.get("protocolApplied", [])[0].get("doseNumberPositiveInt"),
        "VACCINE_PRODUCT_CODE": resource_json.get("vaccineCode", {}).get("coding", [])[0].get("code"),
        "VACCINE_PRODUCT_TERM": resource_json.get("vaccineCode", {}).get("coding", [])[0].get("display"),
        "VACCINE_MANUFACTURER": resource_json.get("manufacturer", {}).get("display"),
        "BATCH_NUMBER": resource_json.get("lotNumber"),
        "EXPIRY_DATE": resource_json.get("expirationDate"),
        "SITE_OF_VACCINATION_CODE": resource_json.get("site", {}).get("coding", [])[0].get("code"),
        "SITE_OF_VACCINATION_TERM": resource_json.get("site", {}).get("coding", [])[0].get("display"),
        "ROUTE_OF_VACCINATION_CODE": resource_json.get("route", {}).get("coding", [])[0].get("code"),
        "ROUTE_OF_VACCINATION_TERM": resource_json.get("route", {}).get("coding", [])[0].get("display"),
        "DOSE_AMOUNT": resource_json.get("doseQuantity", {}).get("value"),
        "DOSE_UNIT_CODE": resource_json.get("doseQuantity", {}).get("code"),
        "DOSE_UNIT_TERM": resource_json.get("doseQuantity", {}).get("unit"),
        "INDICATION_CODE": resource_json.get("reasonCode", [])[0].get("coding", [])[0].get("code"),
        "LOCATION_CODE": resource_json.get("location", {}).get("identifier", {}).get("value"),
        "LOCATION_CODE_TYPE_URI": resource_json.get("location", {}).get("identifier", {}).get("system"),
    }
    if isinstance(flat_dict["PERSON_FORENAME"], list):
        flat_dict["PERSON_FORENAME"] = ' '.join(flat_json["PERSON_FORENAME"])

    # PERFORMING_PROFESSIONAL_FORENAME
    if isinstance(flat_dict["PERFORMING_PROFESSIONAL_FORENAME"], list):
        flat_dict["PERFORMING_PROFESSIONAL_FORENAME"] = ' '.join(flat_dict["PERFORMING_PROFESSIONAL_FORENAME"])
    flat_json = json.dumps(flat_dict)
    return flat_json
