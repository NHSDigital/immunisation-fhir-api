# This class is copied from the e2e project
# @TODO: replace with a solution for shared code
class OperationName:
    """String enums for the name of each endpoint operation"""

    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SEARCH = "SEARCH"

class EventName:
    """String enums for the name of each endpoint operation"""

    REMOVE = "REMOVE"
    INSERT = "INSERT"
    UPDATE = "UPDATE"

class ActionFlag:
    NEW = "NEW"
    DELETE = "DELETE"
    UPDATE = "UPDATE"

    



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
