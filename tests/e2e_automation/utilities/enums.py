from enum import Enum

class Operation(Enum):
   created = "CREATE" 
   updated = "UPDATE" 
   deleted = "DELETE" 
   
class ActionFlag(Enum):
   created = "NEW" 
   updated = "UPDATE" 
   deleted = "DELETE" 
   
class SupplierNameWithODSCode(Enum):
   MAVIS= "V0V8L"
   SONAR= "8HK48"
   RAVS = "X8E5B" 
   PINNACLE = "8J1100001" 
   EMIS = "YGJ"
   TPP = "YGA" 
   MEDICUS = "YGMYW" 
   CEGEDIM = "YGM04"
   Postman_Auth = "Postman_Auth"
   
class GenderCode(Enum):
    male = "1"
    female = "2"
    unknown = "0"
    other = "9"

class ActionMap(Enum):
    new     = (Operation.created, ActionFlag.created)
    update  = (Operation.updated, ActionFlag.updated)
    delete  = (Operation.deleted, ActionFlag.deleted)
    created = (Operation.created, ActionFlag.created)
    updated = (Operation.updated, ActionFlag.updated)
    deleted = (Operation.deleted, ActionFlag.deleted)

    @property
    def operation(self):
        return self.value[0]

    @property
    def action_flag(self):
        return self.value[1]

