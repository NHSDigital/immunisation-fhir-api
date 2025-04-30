import boto3
import json
import os
import time
from datetime import datetime, timedelta
import uuid
import logging
from botocore.exceptions import ClientError
from log_firehose import FirehoseLogger
from Converter import Converter
from helpers.mappings import OperationName, EventName


class DeltaData:
    def __init__(self, delta_table, delta_source):
        self.delta_table = delta_table
        self.delta_source = delta_source

    def get_data(self):
        return self.data


    def get_vaccine_type(self, patientsk) -> str:
        parsed = [str.strip(str.lower(s)) for s in patientsk.split("#")]
        return parsed[0]
        
        
    def write_to_db(self, new_image, imms_id, approximate_creation_time, expiry_time_epoch):
        try:
            vaccine_type = self.get_vaccine_type(new_image["PatientSK"]["S"])
            supplier_system = new_image["SupplierSystem"]["S"]
            if supplier_system not in ("DPSFULL", "DPSREDUCED"):
                operation = new_image["Operation"]["S"]
                if operation == OperationName.CREATE:
                    operation = "NEW"
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
            return response, error_records
        except Exception as e:
            print(f"Error writing to DB: {e}")
            return None