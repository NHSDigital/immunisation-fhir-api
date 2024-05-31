from enum import Enum


class EndpointOperationNames(Enum):
    """String enums for the name of each endpoint operation"""

    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SEARCH = "SEARCH"


class VaccineTypes:
    """Vaccine types"""

    covid_19: str = "COVID19"
    flu: str = "FLU"
    hpv: str = "HPV"
    mmr: str = "MMR"


vaccine_type_mappings = [
    (["840539006"], VaccineTypes.covid_19),
    (["6142004"], VaccineTypes.flu),
    (["240532009"], VaccineTypes.hpv),
    (["14189004", "36653000", "36989005"], VaccineTypes.mmr),
]
