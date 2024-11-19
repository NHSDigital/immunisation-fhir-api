import json
def convert_to_flat_json(resource_json, operation):
    gender_map = {"male": "1", "female": "2", "other": "9", "unknown": "0"}
    operation = operation.lower()
    def get_person_details(resource_json, resource_type):
        for res in resource_json.get("contained", []):
            if res.get("resourceType", "").lower() == resource_type:
                given_name = res.get("name", [{}])[0].get("given", None)
                family_name = res.get("name", [{}])[0].get("family", None)
                return given_name, family_name
        return None, None
    
    person_given_name, person_family_name = get_person_details(resource_json, "patient")
    professional_given_name, professional_family_name = get_person_details(resource_json, "practitioner")

    flat_dict = {
            "NHS_NUMBER": next(
                (identifier.get("value", None)
                for contained_resource in resource_json.get("contained", [])
                if contained_resource.get("resourceType") == "Patient"
                for identifier in contained_resource.get("identifier", [])
                if identifier.get("system") == "https://fhir.nhs.uk/Id/nhs-number"),
                None
            ),
            "PERSON_FORENAME": person_given_name,
            "PERSON_SURNAME": person_family_name,
            "PERSON_DOB": next(
                (contained_resource.get("birthDate", None)
                for contained_resource in resource_json.get("contained", [])
                if contained_resource.get("resourceType") == "Patient"),
                None
            ),
            "PERSON_GENDER_CODE": gender_map.get(next(
                (contained_resource.get("gender", None)
                for contained_resource in resource_json.get("contained", [])
                if contained_resource.get("resourceType") == "Patient"),
                None
            )),
            "PERSON_POSTCODE": next(
                (address.get("postalCode", None)
                for contained_resource in resource_json.get("contained", [])
                if contained_resource.get("resourceType") == "Patient"
                for address in contained_resource.get("address", [])),
                None
            ),
            "DATE_AND_TIME": resource_json.get("occurrenceDateTime", None),
            "SITE_CODE": next(
                (performer.get("actor", {}).get("identifier", {}).get("value", None)
                for performer in resource_json.get("performer", [])
                if performer.get("actor", {}).get("type") == "Organization"),
                None
            ),
            "SITE_CODE_TYPE_URI": next(
                (performer.get("actor", {}).get("identifier", {}).get("system", None)
                for performer in resource_json.get("performer", [])
                if performer.get("actor", {}).get("type") == "Organization"),
                None
            ),
            "UNIQUE_ID": resource_json.get("identifier", [{}])[0].get("value", None),
            "UNIQUE_ID_URI": resource_json.get("identifier", [{}])[0].get("system", None),
            "ACTION_FLAG": operation,
            "PERFORMING_PROFESSIONAL_FORENAME": professional_given_name,
            "PERFORMING_PROFESSIONAL_SURNAME": professional_family_name,
            "RECORDED_DATE": resource_json.get("recorded", None),
            "PRIMARY_SOURCE": str(resource_json.get("primarySource", None)).lower(),
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