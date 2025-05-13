from helpers.mappings import EventName, Operation
from test_resource_data import get_test_data_resource
import json
from typing import List

class RecordConfig:
    event_name: str
    operation: str
    # supplier: str
    pk: str
    def __init__(self, event_name, operation, imms_id, expected_action_flag=None, supplier="EMIS"):
        self.event_name = event_name
        self.operation = operation
        self.supplier = supplier
        self.imms_id = imms_id
        self.expected_action_flag = expected_action_flag

def get_multi_record_event(records_config: List[RecordConfig]):
    records = []
    for config in records_config:
        # Extract values from the config dictionary
        imms_id = config.imms_id
        event_name = config.event_name
        operation = config.operation
        supplier = config.supplier

        # Generate record using the provided configuration
        records.append(
            get_test_event_record(
                imms_id=imms_id,
                event_name=event_name,
                operation=operation,
                supplier=supplier,
            )
        )

    return {"Records": records}

def get_test_event(event_name=EventName.CREATE, operation=Operation.CREATE, supplier="EMIS", imms_id="12345"):
    """Create test event for the handler function."""
    return {
        "Records": [
            get_test_event_record(imms_id, event_name, operation, supplier)
        ]
    }

def get_test_event_record(imms_id, event_name, operation, supplier="EMIS"):
    pk = f"covid#{imms_id}"
    if operation != Operation.DELETE_PHYSICAL:
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
            "eventName": event_name,
            "dynamodb": {
                "ApproximateCreationDateTime": 1690896000,
                "Keys": {
                    "PK": {"S": pk},
                    "PatientSK": {"S": pk},
                    "SupplierSystem": {"S": supplier},
                    "Resource": {
                        "S": json.dumps(get_test_data_resource()),
                    }
                }
            }
        }