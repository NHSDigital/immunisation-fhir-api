from enum import Enum


""" 
    Define enums for event names, operations, and action flags. 
    
    # case              eventName operation actionFlag
    ----------------- --------- --------- ----------
    create            INSERT    CREATE    NEW
    update            MODIFY    UPDATE    UPDATE
    logically delete  MODIFY    DELETE    DELETE
    physically delete REMOVE    REMOVE    -
"""

class EventName(Enum):
    CREATE = "INSERT"
    UPDATE = "MODIFY"
    DELETE_LOGICAL = "MODIFY"
    DELETE_PHYSICAL = "REMOVE"
    
class Operation(Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE_LOGICAL = "DELETE"
    DELETE_PHYSICAL = "REMOVE"

class ActionFlag(Enum):
    CREATE = "NEW"
    UPDATE = "UPDATE"
    DELETE_LOGICAL = "DELETE"
