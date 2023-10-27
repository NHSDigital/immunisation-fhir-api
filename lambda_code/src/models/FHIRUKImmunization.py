from fhir.resources.immunization import Immunization as FHIRImmunization
from fhir.resources.patient import Patient as FHIRPatient
from fhir.resources.organization import Organization as FHIROrganization
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.practitioner import Practitioner as FHIRPractitioner
import datetime
import json


class UKFHIRImmunization:
    def __init__(self, *args, **kwargs):

        self.immunization: FHIRImmunization = None
        self.patient: FHIRPatient = None
        self.recorded: datetime.date = None
        self.reportOrigin: CodeableConcept = None
        self.reasonCode: CodeableConcept = []
        self.manufacturer: FHIROrganization = None
        self.actor: FHIRPractitioner = None

    def get_immunization(self):
        return self.immunization.json()

    def get_patient(self):
        return self.patient.json()

    def get_manufacturer(self):
        return self.manufacturer.json()

    def get_actor(self):
        return {
            "actor": json.loads(self.actor.json())
        }  # Matching representation to that of Expected JSON

    def get_report_origin(self):
        return self.reportOrigin.json()

    def get_reason_code(self):
        if not self.reasonCode:
            return []  # Return an empty list if self.reasonCode is empty

        # Serialize each CodeableConcept object in the list to JSON
        reason_code_json_list = [
            json.loads(reason_code.json()) for reason_code in self.reasonCode
        ]
        return json.dumps(reason_code_json_list)

    def get_recorded(self):
        return self.recorded.isoformat() if self.recorded else None
