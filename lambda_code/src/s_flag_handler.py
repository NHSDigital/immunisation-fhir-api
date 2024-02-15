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
            for record in result["contained"]
            if record["resourceType"] == "QuestionnaireResponse"
        ),
        None,
    )

    contained_patient = next(
        (
            record
            for record in result["contained"]
            if record["resourceType"] == "Patient"
        ),
        None,
    )

    contained_practitioner = next(
        (
            record
            for record in result["contained"]
            if record["resourceType"] == "Practitioner"
        ),
        None,
    )

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

    # Handle Questionnaire removals
    questionnaire_items_to_remove = ["Consent"]
    contained_questionnaire["item"] = [
        item
        for item in contained_questionnaire["item"]
        if "linkId" not in item or item["linkId"] not in questionnaire_items_to_remove
    ]

    # Handle Patient removals
    patient_items_to_remove = ["name", "gender", "birthDate", "address"]
    for item in patient_items_to_remove:
        try:
            del contained_patient[item]
        except KeyError:
            pass

    # Handle Practitioner removals
    practitioner_items_to_remove = ["identifier", "name"]
    for item in practitioner_items_to_remove:
        try:
            del contained_practitioner[item]
        except KeyError:
            pass

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
