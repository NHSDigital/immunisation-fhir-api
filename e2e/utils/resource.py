import copy
import json
import os
import uuid

from .constants import valid_nhs_number1, mmr_code, flu_code

current_directory = os.path.dirname(os.path.realpath(__file__))


def load_example(path: str) -> dict:
    with open(f"{current_directory}/../../specification/components/examples/{path}") as f:
        return json.load(f)


def create_an_imms_obj(imms_id: str = str(uuid.uuid4()),
                       nhs_number=valid_nhs_number1,
                       disease_code=None) -> dict:
    imms = copy.deepcopy(load_example("Immunization/POST-Immunization.json"))
    if disease_code:
        imms["extension"][0]["valueCodeableConcept"]["coding"][0]["code"] = disease_code
        if disease_code == mmr_code:
            imms = copy.deepcopy(load_example("Immunization/POST-mockMMRcode1-Immunization.json"))
        if disease_code == flu_code:
            imms = copy.deepcopy(load_example("Immunization/POST-822851000000102-Immunization.json"))
    imms["id"] = imms_id
    imms["identifier"][0]["value"] = str(uuid.uuid4())
    imms["contained"][1]["identifier"][0]["value"] = nhs_number

    return imms


def get_patient_id(imms: dict) -> str:
    patients = [resource for resource in imms["contained"] if resource["resourceType"] == "Patient"]
    return patients[0]["identifier"][0]["value"]


def get_disease_type(imms: dict) -> str:
    """find the vaccine code in the resource and map it to disease-type"""
    disease_code_to_type_map = {
        # Only add values that we use in the examples. See the mappings.py in the backend code for full dictionary
        "1324681000000101": "COVID19"
    }
    value_codeable_concept_coding = [
        x
        for x in imms["extension"]
        if x.get("url") == "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
    ][0]["valueCodeableConcept"]["coding"]

    vaccination_procedure_code = [
        x
        for x in value_codeable_concept_coding
        if x.get("system") == "http://snomed.info/sct"
    ][0]["code"]

    return disease_code_to_type_map[vaccination_procedure_code]


def get_questionnaire_items(imms: dict):
    questionnaire = next(
        contained
        for contained in imms["contained"]
        if contained["resourceType"] == "QuestionnaireResponse"
    )
    return questionnaire["item"]
