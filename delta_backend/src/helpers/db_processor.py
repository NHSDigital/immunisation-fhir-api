import json
import uuid
from Converter import Converter


class DbProcessor:
    def __init__(self, delta_table, delta_source, logger):
        self.delta_table = delta_table
        self.delta_source = delta_source
        self.logger = logger

    def get_data(self):
        return self.data     
    
    def remove(self, imms_id, operation,
                    approximate_creation_time, expiry_time_epoch):
            response = self.delta_table.put_item(
                Item={
                    "PK": str(uuid.uuid4()),
                    "ImmsID": imms_id,
                    "Operation": operation,
                    "VaccineType": "default",
                    "SupplierSystem": "default",
                    "DateTimeStamp": approximate_creation_time.isoformat(),
                    "Source": self.delta_source,
                    "Imms": "",
                    "ExpiresAt": expiry_time_epoch,
                }
            )
            return response
        
    def write(self, new_image, imms_id, operation, vaccine_type, supplier_system,
                    approximate_creation_time, expiry_time_epoch):
        try:
            # vaccine_type = self.get_vaccine_type(new_image["PatientSK"]["S"])
            # supplier_system = new_image["SupplierSystem"]["S"]
            # if supplier_system not in ("DPSFULL", "DPSREDUCED"):
            #     operation = new_image["Operation"]["S"]
            #     if operation == OperationName.CREATE:
            #         operation = ActionFlag.CREATE
            resource_json = json.loads(new_image["Resource"]["S"])
            FHIRConverter = Converter(json.dumps(resource_json))
            flat_json = FHIRConverter.runConversion(resource_json)  # Get the flat JSON
            error_records = FHIRConverter.getErrorRecords()
            flat_json[0]["ACTION_FLAG"] = operation
            response = self.delta_table.put_item(
                Item={
                    "PK": str(uuid.uuid4()),
                    "ImmsID": imms_id,
                    "Operation": operation,
                    "VaccineType": vaccine_type,
                    "SupplierSystem": supplier_system,
                    "DateTimeStamp": approximate_creation_time.isoformat(),
                    "Source": self.delta_source,
                    "Imms": str(flat_json),
                    "ExpiresAt": expiry_time_epoch,
                }
            )
            return response, operation, error_records
        except Exception as e:
            print(f"Error writing to DB: {e}")
            return None