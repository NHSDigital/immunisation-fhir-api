class EventName:
    CREATE = "INSERT"
    UPDATE = "MODIFY"
    DELETE_LOGICAL = "MODIFY"
    DELETE_PHYSICAL = "REMOVE"


class EndpointOperationName:
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    
class OperationName:
    CREATE = "NEW"
    UPDATE = "UPDATE"
    DELETE_LOGICAL = "DELETE"
    DELETE_PHYSICAL = "REMOVE"

ActionFlag = OperationName

class VaccineTypes:
    """Vaccine types"""

    covid_19: str = "COVID19"
    flu: str = "FLU"
    hpv: str = "HPV"
    mmr: str = "MMR"
    rsv: str = "RSV"


vaccine_type_mappings = [
    (["840539006"], VaccineTypes.covid_19),
    (["6142004"], VaccineTypes.flu),
    (["240532009"], VaccineTypes.hpv),
    (["14189004", "36653000", "36989005"], VaccineTypes.mmr),
    (["55735004"], VaccineTypes.rsv),
]
