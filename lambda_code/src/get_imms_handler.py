import uuid
from fhir_controller import FhirController, make_controller
from models.errors import Severity, Code, create_operation_outcome


def get_imms_handler(event, context):
    return get_immunization_by_id(event, make_controller())


def get_immunization_by_id(event, controller: FhirController):
    try:
        return controller.get_immunization_by_id(event)
    except Exception as e:
        exp_error = create_operation_outcome(resource_id=str(uuid.uuid4()), severity=Severity.error,
                                             code=Code.server_error,
                                             diagnostics=str(e))
        return FhirController.create_response(500, exp_error.json())
