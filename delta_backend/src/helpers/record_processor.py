import json
import time
from datetime import datetime, timedelta
import logging
from helpers.db_processor import DbProcessor
from helpers.mappings import OperationName, EventName, ActionFlag
from helpers.processor_utils import get_op_outcome

class RecordProcessor:
    @staticmethod
    def get_vaccine_type(patientsk) -> str:
        parsed = [str.strip(str.lower(s)) for s in patientsk.split("#")]
        return parsed[0]

    def __init__(self, delta_table, delta_source, log_data, db_processor: DbProcessor, firehose_logger, firehose_log, logger: logging.Logger):
        self.delta_table = delta_table
        self.delta_source = delta_source
        self.log_data = log_data
        self.db_processor = db_processor
        self.firehose_logger = firehose_logger
        self.firehose_log = firehose_log
        self.logger = logger

    def get_operation(self, record):
        if record["eventName"] == EventName.DELETE_PHYSICAL:
            return OperationName.DELETE_PHYSICAL

    def process_record(self, record):
        start = time.time()
        self.log_data["date_time"] = str(datetime.now())
        approximate_creation_time = datetime.utcfromtimestamp(record["dynamodb"]["ApproximateCreationDateTime"])
        expiry_time = approximate_creation_time + timedelta(days=30)
        expiry_time_epoch = int(expiry_time.timestamp())
        error_records = []
        response = str()
        imms_id = str()
        operation = str()
        if record["eventName"] != EventName.DELETE_PHYSICAL:
            new_image = record["dynamodb"]["NewImage"]
            imms_id = new_image["PK"]["S"].split("#")[1]
            supplier_system = new_image["SupplierSystem"]["S"]
            if supplier_system not in ("DPSFULL", "DPSREDUCED"):
                vaccine_type = self.get_vaccine_type(new_image["PatientSK"]["S"])
                supplier_system = new_image["SupplierSystem"]["S"]
                if supplier_system not in ("DPSFULL", "DPSREDUCED"):
                    operation = new_image["Operation"]["S"]
                    if operation == OperationName.CREATE:
                        operation = ActionFlag.CREATE
                response, error_records = self.db_processor.write(new_image, imms_id, operation,
                                                                    vaccine_type, supplier_system,
                                                                    approximate_creation_time,
                                                                    expiry_time_epoch)
            else:
                self.log_operation( 200, "Record from DPS skipped", info_msg=f"Record from DPS skipped for {imms_id}")
                return {"statusCode": 200, "body": f"Record from DPS skipped for {imms_id}"}
        else:
            operation = OperationName.DELETE_PHYSICAL
            new_image = record["dynamodb"]["Keys"]
            self.logger.info(f"Record to delta:{new_image}")
            imms_id = new_image["PK"]["S"].split("#")[1]
            response = self.db_processor.remove(imms_id, operation,
                                            approximate_creation_time, expiry_time_epoch)
        end = time.time()
        self.log_data["time_taken"] = f"{round(end - start, 5)}s"
        operation_outcome = {"record": imms_id, "operation_type": operation}
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            log = ""
            if error_records:
                msg = "Partial success: successfully synced into delta, but issues found within record"
                log = f"{msg} {imms_id}"
                operation_outcome = get_op_outcome( 207, f"{msg} {json.dumps(error_records)}")
            else:
                log = f"Record Successfully created for {imms_id}"
                operation_outcome = get_op_outcome( 200, "Successfully synched into delta")

            self.log_send_op_outcome(operation_outcome, info_msg=log)
            return {"statusCode": 200, "body": "Records processed successfully"}
        else:
            self.log_operation(500, "Exception", info_msg=f"Record NOT created for {imms_id}")
            return {"statusCode": 500, "body": "Records not processed successfully"}

    def log_operation(self, status_code: int, status_desc: str, diagnostics: str = None, record: str = None, operation_type: str = None, info_msg: str = None, exception_msg: str = None):
        """
        Handles operation failures by constructing the operation_outcome and logging the result.
        """
        operation_outcome = get_op_outcome( status_code=status_code, status_desc=status_desc, diagnostics=diagnostics, record=record, operation_type=operation_type)
        self.log_send_op_outcome(operation_outcome, info_msg=info_msg, exception_msg=exception_msg)

    def log_send_op_outcome(self, operation_outcome: dict, info_msg: str = None, exception_msg: str = None):
        """
        Logs the operation outcome, updates the Firehose log, and sends the log.
        """
        if exception_msg:
            self.logger.info(exception_msg)

        self.log_data["operation_outcome"] = operation_outcome
        self.firehose_log["event"] = self.log_data
        self.firehose_logger.send_log(self.firehose_log)

        if info_msg:
            self.logger.info(info_msg)

