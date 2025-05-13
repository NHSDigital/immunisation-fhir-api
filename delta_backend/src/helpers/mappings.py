""" 
    Define enums for event names, operations, and action flags. 
    
    # case            eventName operation actionFlag
    ----------------- --------- --------- ----------
    create            INSERT    CREATE    NEW
    update            MODIFY    UPDATE    UPDATE
    logically delete  MODIFY    DELETE    DELETE
    physically delete REMOVE    REMOVE    N/A
"""

class EventName():
    CREATE = "INSERT"
    UPDATE = "MODIFY"
    DELETE_LOGICAL = "MODIFY"
    DELETE_PHYSICAL = "REMOVE"
    
class Operation():
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE_LOGICAL = "DELETE"
    DELETE_PHYSICAL = "REMOVE"

class ActionFlag():
    CREATE = "NEW"
    UPDATE = "UPDATE"
    DELETE_LOGICAL = "DELETE"
