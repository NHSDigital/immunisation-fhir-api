"""Mappings for converting vaccine type into target disease FHIR element"""

from enum import Enum
from typing import Dict, List
from constants import Urls


class Vaccine(Enum):
    """Disease Codes"""

    COVID_19: str = "COVID19"
    FLU: str = "FLU"
    MMR: str = "MMR"
    RSV: str = "RSV"


class Disease(Enum):
    """Disease Codes"""

    COVID_19: str = "COVID19"
    FLU: str = "FLU"
    MEASLES: str = "MEASLES"
    MUMPS: str = "MUMPS"
    RUBELLA: str = "RUBELLA"
    RSV: str = "RSV"


class DiseaseCode(Enum):
    """Disease Codes"""

    COVID_19: str = "840539006"
    FLU: str = "6142004"
    MEASLES: str = "14189004"
    MUMPS: str = "36989005"
    RUBELLA: str = "36653000"
    RSV: str = "55735004"


class DiseaseDisplayTerm(Enum):
    """Disease display terms which correspond to disease codes"""

    COVID_19: str = "Disease caused by severe acute respiratory syndrome coronavirus 2"
    FLU: str = "Influenza"
    MEASLES: str = "Measles"
    MUMPS: str = "Mumps"
    RUBELLA: str = "Rubella"
    RSV: str = "Respiratory syncytial virus infection (disorder)"


VACCINE_DISEASE_MAPPING: Dict[Vaccine, List[Disease]] = {
    Vaccine.COVID_19: [Disease.COVID_19],
    Vaccine.FLU: [Disease.FLU],
    Vaccine.MMR: [Disease.MEASLES, Disease.MUMPS, Disease.RUBELLA],
    Vaccine.RSV: [Disease.RSV],
}


def map_target_disease(vaccine: Vaccine) -> list:
    """Returns the target disease element for the given vaccine type using the vaccine_disease_mapping"""
    diseases = VACCINE_DISEASE_MAPPING.get(vaccine, [])
    return [
        {
            "coding": [
                {
                    "system": Urls.SNOMED,
                    "code": DiseaseCode[disease.name].value,
                    "display": DiseaseDisplayTerm[disease.name].value,
                }
            ]
        }
        for disease in diseases
    ]
