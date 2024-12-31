"""Function to send the request directly to lambda (or return appropriate diagnostics if this is not possible)"""

from models.errors import MessageNotSuccessfulError
from fhir_batch_service import ImmunizationBatchService
from fhir_batch_repository import ImmunizationBatchRepository

def make_batch_controller():
    immunization_repo = ImmunizationBatchRepository()
    fhir_service = ImmunizationBatchService(immunization_repo=immunization_repo)
    return ImmunizationBatchController(immunization_repo=immunization_repo, fhir_service=fhir_service)

class ImmunizationBatchController:
    def __init__(
        self,
        immunization_repo: ImmunizationBatchRepository,
        fhir_service: ImmunizationBatchService,
    ):
        self.immunization_repo = immunization_repo
        self.fhir_service = fhir_service
    
    def send_request_to_dynamo(self, message_body: dict, table: any, is_present: bool):
        """
        Sends request to the Imms API (unless there was a failure at the recordprocessor level). Returns the imms id.
        If message is not successfully received and accepted by the Imms API raises a MessageNotSuccessful Error.
        """
        if incoming_diagnostics := message_body.get("diagnostics"):
            raise MessageNotSuccessfulError(incoming_diagnostics)

        supplier = message_body.get("supplier")
        fhir_json = message_body.get("fhir_json")
        vax_type = message_body.get("vax_type")
        # file_key = message_body.get("file_key")
        # row_id = message_body.get("row_id")
        operation_requested = message_body.get("operation_requested")

        # Send request to Imms FHIR API and return the imms_id
        function_map = {"CREATE": self.fhir_service.create_immunization, "UPDATE": self.fhir_service.update_immunization, "DELETE": self.fhir_service.delete_immunization}
        return function_map[operation_requested](immunization=fhir_json, supplier_system=supplier, vax_type=vax_type, table=table, is_present=is_present)
