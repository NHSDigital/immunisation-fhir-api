import json
def convert_to_flat_json(resource_json, operation):
    flat_dict = {
                    "NHS_NUMBER": resource_json.get("contained", [None, {}])[1].get("identifier", [{}])[0].get("value", None),
                    "PERSON_FORENAME": resource_json.get("contained", [None, {}])[1].get("name", [{}])[0].get("given", None),
                    "PERSON_SURNAME": resource_json.get("contained", [None, {}])[1].get("name", [{}])[0].get("family", None),
                    "PERSON_DOB": resource_json.get("contained", [None, {}])[1].get("birthDate", None),
                    "PERSON_GENDER_CODE": resource_json.get("contained", [None, {}])[1].get("gender", None),
                    "PERSON_POSTCODE": resource_json.get("contained", [None, {}])[1].get("address", [{}])[0].get("postalCode", None),
                    "DATE_AND_TIME": resource_json.get("occurrenceDateTime", None),
                    "SITE_CODE": resource_json.get("performer", [None, {}])[1].get("actor", {}).get("identifier", {}).get("value", None),
                    "SITE_CODE_TYPE_URI": resource_json.get("performer", [None, {}])[1].get("actor", {}).get("identifier", {}).get("system", None),
                    "UNIQUE_ID": resource_json.get("identifier", [{}])[0].get("value", None),
                    "UNIQUE_ID_URI": resource_json.get("identifier", [{}])[0].get("system", None),
                    "ACTION_FLAG": "new",  # Based on the operation 'CREATE'
                    "PERFORMING_PROFESSIONAL_FORENAME": resource_json.get("contained", [None, {}])[0].get("name", [{}])[0].get("given", None),
                    "PERFORMING_PROFESSIONAL_SURNAME": resource_json.get("contained", [None, {}])[0].get("name", [{}])[0].get("family", None),
                    "RECORDED_DATE": resource_json.get("recorded", None),
                    "PRIMARY_SOURCE": resource_json.get("primarySource", None),
                    "VACCINATION_PROCEDURE_CODE": resource_json.get("extension", [{}])[0].get("valueCodeableConcept", {}).get("coding", [{}])[0].get("code", None),
                    "VACCINATION_PROCEDURE_TERM": resource_json.get("extension", [{}])[0].get("valueCodeableConcept", {}).get("coding", [{}])[0].get("display", None),
                    "DOSE_SEQUENCE": resource_json.get("protocolApplied", [{}])[0].get("doseNumberPositiveInt", None),
                    "VACCINE_PRODUCT_CODE": resource_json.get("vaccineCode", {}).get("coding", [{}])[0].get("code", None),
                    "VACCINE_PRODUCT_TERM": resource_json.get("vaccineCode", {}).get("coding", [{}])[0].get("display", None),
                    "VACCINE_MANUFACTURER": resource_json.get("manufacturer", {}).get("display", None),
                    "BATCH_NUMBER": resource_json.get("lotNumber", None),
                    "EXPIRY_DATE": resource_json.get("expirationDate", None),
                    "SITE_OF_VACCINATION_CODE": resource_json.get("site", {}).get("coding", [{}])[0].get("code", None),
                    "SITE_OF_VACCINATION_TERM": resource_json.get("site", {}).get("coding", [{}])[0].get("display", None),
                    "ROUTE_OF_VACCINATION_CODE": resource_json.get("route", {}).get("coding", [{}])[0].get("code", None),
                    "ROUTE_OF_VACCINATION_TERM": resource_json.get("route", {}).get("coding", [{}])[0].get("display", None),
                    "DOSE_AMOUNT": resource_json.get("doseQuantity", {}).get("value", None),
                    "DOSE_UNIT_CODE": resource_json.get("doseQuantity", {}).get("code", None),
                    "DOSE_UNIT_TERM": resource_json.get("doseQuantity", {}).get("unit", None),
                    "INDICATION_CODE": resource_json.get("reasonCode", [{}])[0].get("coding", [{}])[0].get("code", None),
                    "LOCATION_CODE": resource_json.get("location", {}).get("identifier", {}).get("value", None),
                    "LOCATION_CODE_TYPE_URI": resource_json.get("location", {}).get("identifier", {}).get("system", None)
                }
    if isinstance(flat_dict["PERSON_FORENAME"], list):
        flat_dict["PERSON_FORENAME"] = ' '.join(flat_dict["PERSON_FORENAME"])

    # PERFORMING_PROFESSIONAL_FORENAME
    if isinstance(flat_dict["PERFORMING_PROFESSIONAL_FORENAME"], list):
        flat_dict["PERFORMING_PROFESSIONAL_FORENAME"] = ' '.join(flat_dict["PERFORMING_PROFESSIONAL_FORENAME"])
    flat_json = json.dumps(flat_dict)
    return flat_json
