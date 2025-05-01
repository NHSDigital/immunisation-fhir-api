import json
from helpers.mappings import OperationName, EventName
from test_resource_data import get_test_data_resource


def get_event(event_name=EventName.CREATE, operation=OperationName.CREATE, supplier="EMIS", n_records=1):
    """Create test event for the handler function."""
    return {
        "Records": [
            get_event_record(f"covid#{i+1}2345", event_name, operation, supplier)
            for i in range(n_records)
        ]
    }

def get_event_record(pk, event_name=EventName.CREATE, operation=OperationName.CREATE, supplier="EMIS"):
    if operation != OperationName.DELETE_PHYSICAL:
        return{
            "eventName": event_name,
            "dynamodb": {
                "ApproximateCreationDateTime": 1690896000,
                "NewImage": {
                    "PK": {"S": pk},
                    "PatientSK": {"S": pk},
                    "IdentifierPK": {"S": "system#1"},
                    "Operation": {"S": operation},
                    "SupplierSystem": {"S": supplier},
                    "Resource": {
                        "S": json.dumps(get_test_data_resource()),
                    }
                }
            }
        }
    else:
        return {
            "eventName": EventName.DELETE_PHYSICAL,
            "dynamodb": {
                "ApproximateCreationDateTime": 1690896000,
                "Keys": {
                    "PK": {"S": pk},
                    "PatientSK": {"S": pk},
                    "SupplierSystem": {"S": "EMIS"},
                    "Resource": {
                        "S": json.dumps(get_test_data_resource()),
                    }
                }
            }
        }
