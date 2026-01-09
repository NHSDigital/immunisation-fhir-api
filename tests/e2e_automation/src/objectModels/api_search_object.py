from dataclasses import asdict, dataclass, field
from urllib.parse import urlencode

@dataclass
class ImmunizationRequest:
    patient_identifier: str
    immunization_target: str 
    include: str 
    date_from: str 
    date_to: str 

def set_request_data(nhs_number, target, date_from :str = None, date_to:str = None, include:str = "Immunization:patient") -> ImmunizationRequest:
    return ImmunizationRequest(
        patient_identifier=f"https://fhir.nhs.uk/Id/nhs-number|{nhs_number}",
        immunization_target=target,
        include=include,
        date_from=date_from,
        date_to=date_to
)

def convert_to_form_data(request: ImmunizationRequest) -> str:
    data_dict = asdict(request)

    field_mapping = {
        "patient_identifier": "patient.identifier",
        "immunization_target": "-immunization.target",
        "include": "_include",
        "date_from": "-date.from",
        "date_to": "-date.to"
    }
    
    clean_data = {field_mapping[key]: value for key, value in data_dict.items() if value is not None}

    include_value = clean_data.pop("_include", None)

    encoded_data = urlencode(clean_data, safe= "|")

    if include_value:
        encoded_data += f"&_include={include_value}"

    return encoded_data