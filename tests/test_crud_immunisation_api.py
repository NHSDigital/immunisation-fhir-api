import uuid
import copy

from .configuration.config import valid_nhs_number1
from .example_loader import load_example


def create_an_imms_obj(imms_id: str = str(uuid.uuid4()), nhs_number=valid_nhs_number1) -> dict:
    imms = copy.deepcopy(load_example("Immunization/POST-COVID19-Immunization.json"))
    imms["id"] = imms_id
    imms["identifier"][0]["value"] = str(uuid.uuid4())
    imms["contained"][1]["identifier"][0]["value"] = nhs_number
    return imms
