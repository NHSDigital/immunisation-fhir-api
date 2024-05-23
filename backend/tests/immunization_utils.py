"""Immunization utils"""

from fhir.resources.R4B.immunization import Immunization

from tests.utils.values_for_tests import ValidValues
from tests.utils.generic_utils import load_json_data

VALID_NHS_NUMBER = ValidValues.nhs_number


def create_covid_19_immunization(imms_id, nhs_number=VALID_NHS_NUMBER) -> Immunization:
    base_imms = create_covid_19_immunization_dict(imms_id, nhs_number)
    return Immunization.parse_obj(base_imms)

def create_covid_19_immunization_dict(
    imms_id, nhs_number=VALID_NHS_NUMBER, occurrence_date_time="2021-02-07T13:28:17.271+00:00"
):
    immunization_json = load_json_data("completed_covid19_immunization_event.json")
    immunization_json["id"] = imms_id

    [x for x in immunization_json["contained"] if x.get("resourceType") == "Patient"][0]["identifier"][0][
        "value"
    ] = nhs_number

    immunization_json["occurrenceDateTime"] = occurrence_date_time

    return immunization_json
