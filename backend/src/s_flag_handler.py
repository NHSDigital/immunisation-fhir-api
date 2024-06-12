import copy


def handle_s_flag(imms, patient):
    """
    See https://nhsd-confluence.digital.nhs.uk/pages/viewpage.action?pageId=758110223 for details.
    """
    try:
        patient_is_restricted = str.lower(patient["meta"]["security"][0]["code"]) == "r"
    except (KeyError, IndexError):
        return imms

    if not patient_is_restricted:
        return imms

    result = copy.deepcopy(imms)

    contained_questionnaire = next(
        (
            record
            for record in result.get("contained", [])
            if record["resourceType"] == "QuestionnaireResponse"
        ),
        None,
    )

    contained_patient = next(
        (
            record
            for record in result.get("contained", [])
            if record["resourceType"] == "Patient"
        ),
        None,
    )

    contained_practitioner = next(
        (
            record
            for record in result.get("contained", [])
            if record["resourceType"] == "Practitioner"
        ),
        None,
    )

    # Handle Questionnaire SiteCode
    performer_actor_organization = next(
        (
            item
            for item in result["performer"]
            if item.get("actor", {}).get("type") == "Organization"
        ),
        None,
    )

    if performer_actor_organization:
        try:
            performer_actor_organization["actor"]["identifier"]["value"] = "N2N9I"
            performer_actor_organization["actor"]["identifier"][
                "system"
            ] = "https://fhir.nhs.uk/Id/ods-organization-code"
            del performer_actor_organization["actor"]["display"]
        except KeyError:
            pass
        
    if contained_patient:
        try:
            contained_patient["address"][0]["postalCode"] = "ZZ99 3CZ"
        except (KeyError, IndexError):
            pass
    
            
    # Handle Questionnaire removals
    questionnaire_items_to_remove = ["Consent"]
    if contained_questionnaire and contained_questionnaire.get("item"):
        contained_questionnaire["item"] = [
            item
            for item in contained_questionnaire.get("item", [])
            if "linkId" not in item or item["linkId"] not in questionnaire_items_to_remove
    ]

    # Handle reportOrigin
    try:
        del result["reportOrigin"]
    except KeyError:
        pass

    # Handle Location
    try:
        del result["location"]
    except KeyError:
        pass

    return result
