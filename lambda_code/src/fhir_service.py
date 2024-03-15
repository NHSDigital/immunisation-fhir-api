import os

from enum import Enum
from typing import Optional

from fhir.resources.R4B.bundle import Bundle as FhirBundle
from fhir.resources.R4B.bundle import BundleEntry
from fhir.resources.R4B.bundle import BundleLink
from fhir.resources.R4B.immunization import Immunization
from pydantic import ValidationError

from fhir_repository import ImmunizationRepository
from models.errors import (
    InvalidPatientId,
    CustomValidationError,
    ResourceNotFoundError,
    InconsistentIdError,
)
from models.fhir_immunization import ImmunizationValidator
from models.utils.post_validation_utils import MandatoryError, NotApplicableError
from models.utils.generic_utils import nhs_number_mod11_check
from pds_service import PdsService
from s_flag_handler import handle_s_flag
from timer import timed


def get_service_url(
    service_env: str = os.getenv("IMMUNIZATION_ENV"),
    service_base_path: str = os.getenv("IMMUNIZATION_BASE_PATH"),
):
    non_prod = ["internal-dev", "int", "sandbox"]
    if service_env in non_prod:
        subdomain = f"{service_env}."
    elif service_env == "prod":
        subdomain = ""
    else:
        subdomain = "internal-dev."
    return f"https://{subdomain}api.service.nhs.uk/{service_base_path}"


class UpdateOutcome(Enum):
    UPDATE = 0
    CREATE = 1


class FhirService:
    def __init__(
        self,
        imms_repo: ImmunizationRepository,
        pds_service: PdsService,
        validator: ImmunizationValidator = ImmunizationValidator(),
    ):
        self.immunization_repo = imms_repo
        self.pds_service = pds_service
        self.validator = validator

    def get_immunization_by_id(self, imms_id: str) -> Optional[Immunization]:
        imms = self.immunization_repo.get_immunization_by_id(imms_id)

        if not imms:
            return None

        nhs_number = [x for x in imms["contained"] if x.get("resourceType") == "Patient"][0]["identifier"][0]["value"]
        patient = self.pds_service.get_patient_details(nhs_number)
        filtered_immunization = handle_s_flag(imms, patient)
        return Immunization.parse_obj(filtered_immunization)

    def create_immunization(self, immunization: dict) -> Immunization:
        try:
            self.validator.validate(immunization)
        except (ValidationError, ValueError, MandatoryError, NotApplicableError) as error:
            raise CustomValidationError(message=str(error)) from error

        patient = self._validate_patient(immunization)

        imms = self.immunization_repo.create_immunization(immunization, patient)

        return Immunization.parse_obj(imms)

    def update_immunization(self, imms_id: str, immunization: dict) -> (UpdateOutcome, Immunization):
        if immunization.get("id", imms_id) != imms_id:
            raise InconsistentIdError(imms_id=imms_id)
        immunization["id"] = imms_id

        try:
            self.validator.validate(immunization)
        except (ValidationError, ValueError, MandatoryError, NotApplicableError) as error:
            raise CustomValidationError(message=str(error)) from error

        patient = self._validate_patient(immunization)

        try:
            imms = self.immunization_repo.update_immunization(imms_id, immunization, patient)
            return UpdateOutcome.UPDATE, Immunization.parse_obj(imms)
        except ResourceNotFoundError:
            imms = self.immunization_repo.create_immunization(immunization, patient)

            return UpdateOutcome.CREATE, Immunization.parse_obj(imms)

    def delete_immunization(self, imms_id) -> Immunization:
        """
        Delete an Immunization if it exits and return the ID back if successful.
        Exception will be raised if resource didn't exit. Multiple calls to this method won't change
        the record in the database.
        """
        imms = self.immunization_repo.delete_immunization(imms_id)
        return Immunization.parse_obj(imms)

    def search_immunizations(self, nhs_number: str, disease_type: str, params: str) -> FhirBundle:
        """find all instances of Immunization(s) for a patient and specified disease type.
        Returns Bundle[Immunization]
        """
        # TODO: is disease type a mandatory field? (I assumed it is)
        #  i.e. Should we provide a search option for getting Patient's entire imms history?
        if not nhs_number_mod11_check(nhs_number):
            raise InvalidPatientId(nhs_number=nhs_number)
        resources = self.immunization_repo.find_immunizations(nhs_number, disease_type)
        patient = self.pds_service.get_patient_details(nhs_number)
        entries = [BundleEntry(resource=Immunization.parse_obj(handle_s_flag(imms, patient))) for imms in resources]
        fhir_bundle = FhirBundle(
            resourceType="Bundle",
            type="searchset",
            entry=entries,
        )
        url = f"{get_service_url()}/Immunization?{params}"
        fhir_bundle.link = [BundleLink(relation="self", url=url)]
        return fhir_bundle

    @timed
    def _validate_patient(self, imms: dict):
        nhs_number = [x for x in imms["contained"] if x.get("resourceType") == "Patient"][0]["identifier"][0]["value"]
        patient = self.pds_service.get_patient_details(nhs_number)

        if patient:
            return patient
        else:
            raise InvalidPatientId(nhs_number=nhs_number)
