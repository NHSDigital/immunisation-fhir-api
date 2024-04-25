from collections import OrderedDict

import logging
import structlog
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from batch.errors import TransformerUnhandledError, TransformerRowError, ImmunizationApiError, \
    ImmunizationApiUnhandledError
from batch.immunization_api import ImmunizationApi
from batch.parser import DataParser
from batch.report import ReportGenerator, ReportEntry
from batch.transformer import DataRecordTransformer

logger = structlog.get_logger()


@dataclass
class BatchData:
    """The origin of the Batch event."""
    batch_id: str
    object_key: str
    source_bucket: str
    destination_bucket: str
    event_id: str
    event_timestamp: float
    process_timestamp: float
    environment: str


class Action(str, Enum):
    """The action to be taken on the record. The value is determined by the `action_flag` field."""
    CREATE = "new"
    UPDATE = "update"
    DELETE = "delete"


class BatchProcessor:
    headers: List[str]

    def __init__(self, batch_data: BatchData,
                 parser: DataParser,
                 row_transformer: DataRecordTransformer,
                 report_generator: ReportGenerator,
                 api: ImmunizationApi):
        self.parser = parser
        self.row_transformer = row_transformer
        self.report_generator = report_generator
        self.api = api
        self.batch_data = batch_data

        # We create a trace object at the beginning of each row, regardless of the row error.
        self.trace_data = {}

    def process(self) -> None:
        rows = self.parser.parse_rows()
        headers = next(rows)
        self.headers = [h.lower() for h in headers]

        row_no = 0
        for row in rows:
            cur_row_no = row_no
            row_no += 1  # Inc now so it'll be correct in case of an exception

            # Both cor_id and req_id are the same. This way we know this is the source (actor or client)
            cor_id = str(uuid.uuid4())
            self.trace_data = {
                "correlation_id": cor_id,
                "request_id": cor_id,
            }

            raw_record = OrderedDict(zip(self.headers, row))
            if action := self._get_action(raw_record, cur_row_no):
                if record := self._transform(raw_record, cur_row_no):
                    self._send_data(record, action, cur_row_no)

        self.report_generator.close()

    def _transform(self, record: OrderedDict, row: int) -> dict:
        try:
            record = self.row_transformer.transform(record)
            return record
        except (TransformerUnhandledError, TransformerRowError) as e:
            self.report_generator.add_error(ReportEntry(message=str(e)))

            data = self._make_log_data(str(e), row)
            data["type"] = "transform_error"
            data["error_type"] = "handled" if isinstance(e, TransformerRowError) else "unhandled"

            logger.error(data)

    def _send_data(self, data: dict, action: Action, row: int) -> None:
        try:
            if action == Action.DELETE:
                response = self.api.delete_immunization(data, self.trace_data["correlation_id"])
            elif action == Action.UPDATE:
                response = self.api.update_immunization(data, self.trace_data["correlation_id"])
            elif action == Action.CREATE:
                response = self.api.create_immunization(data, self.trace_data["correlation_id"])
            else:
                raise ValueError("Invalid action")  # This should never happen, we have already validated the action

            data = self._make_log_data(f"Immunization {action.value}ed successfully", row)
            data["type"] = "api_success"
            data["request"] = data
            data["response"] = response.text
            logger.info(data)

        except ImmunizationApiError as e:
            report_entry = ReportEntry(message=str(e.response))
            self.report_generator.add_error(report_entry)

            data = self._make_log_data(f"Immunization creation failed", row)
            data["type"] = "api_error"
            data["error_type"] = "handled"
            data["request"] = e.request
            data["response"] = e.response
            logging.log(logging.ERROR, data)
        except ImmunizationApiUnhandledError as e:
            report_entry = ReportEntry(message=str(e.request))
            self.report_generator.add_error(report_entry)

            data = self._make_log_data(f"An error occurred while creating immunization: {e}", row)
            data["type"] = "api_error"
            data["error_type"] = "unhandled"
            logging.log(logging.ERROR, data)

    def _get_action(self, record: OrderedDict, row: int) -> Optional[Action]:
        if action := record.get("action_flag"):
            try:
                return Action(action.lower())
            except ValueError:
                report_entry = ReportEntry(message=str(f"The value for action_flag is invalid: {action}"))
                self.report_generator.add_error(report_entry)

                data = self._make_log_data(f"The value for action_flag is invalid: {action}", row)
                data["type"] = "action_error"
                data["error_type"] = "unhandled"
                logging.log(logging.ERROR, data)

                return None
        else:
            report_entry = ReportEntry(message=str("The action_flag is missing"))
            self.report_generator.add_error(report_entry)

            data = self._make_log_data("The action_flag is missing", row)
            data["type"] = "action_error"
            data["error_type"] = "unhandled"
            logging.log(logging.ERROR, data)

            return None

    def _make_log_data(self, msg: str, row: int) -> dict:
        return {
            "batch_id": self.batch_data.batch_id,
            "message": msg,
            "row": row,
            "timestamp": time.time(),
            **self.trace_data,
        }
