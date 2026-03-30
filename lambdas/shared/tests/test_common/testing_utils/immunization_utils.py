"""Immunization utils."""

from fhir.resources.R4B.immunization import Immunization

from common.models.constants import Constants
from test_common.testing_utils.generic_utils import load_json_data
from test_common.testing_utils.values_for_tests import ValidValues

VALID_NHS_NUMBER = ValidValues.nhs_number


def create_covid_immunization(imms_id, nhs_number=VALID_NHS_NUMBER) -> Immunization:
    base_imms = create_covid_immunization_dict(imms_id, nhs_number)
    return Immunization.parse_obj(base_imms)


def create_covid_immunization_dict(
    imms_id: str,
    nhs_number: str = VALID_NHS_NUMBER,
    occurrence_date_time: str = "2021-02-07T13:28:17+00:00",
    status: str = "completed",
    omit_nhs_number: bool = False,
):
    immunization_json = load_json_data("completed_covid_immunization_event.json")
    immunization_json["id"] = imms_id

    for contained_resource in immunization_json.get("contained", []):
        if contained_resource.get("resourceType") == Constants.PATIENT_RESOURCE_TYPE:
            if omit_nhs_number:
                del contained_resource["identifier"][0]["value"]
            else:
                contained_resource["identifier"][0]["value"] = nhs_number

    immunization_json["occurrenceDateTime"] = occurrence_date_time
    immunization_json["status"] = status

    return immunization_json


def create_covid_immunization_dict_no_id(
    nhs_number=VALID_NHS_NUMBER, occurrence_date_time="2021-02-07T13:28:17.271+00:00"
):
    immunization_json = load_json_data("completed_covid_immunization_event.json")

    [x for x in immunization_json["contained"] if x.get("resourceType") == "Patient"][0]["identifier"][0]["value"] = (
        nhs_number
    )

    immunization_json["occurrenceDateTime"] = occurrence_date_time

    return immunization_json
