import datetime
import os
from enum import Enum
from typing import Optional

from fhir.resources.R4B.bundle import Bundle as FhirBundle, BundleEntry, BundleLink, BundleEntrySearch
from fhir.resources.R4B.immunization import Immunization
from pydantic import ValidationError

import parameter_parser
from fhir_repository import ImmunizationRepository
from models.errors import (
    InvalidPatientId,
    CustomValidationError,
    ResourceNotFoundError,
    InconsistentIdError,
)
from models.fhir_immunization import ImmunizationValidator
from models.utils.generic_utils import (
    nhs_number_mod11_check,
    get_occurrence_datetime,
    create_diagnostics,
)
from models.utils.post_validation_utils import MandatoryError, NotApplicableError
from utils import get_vaccine_type
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
        """
        Get an Immunization by its ID. Return None if not found. If the patient doesn't have an NHS number,
        return the Immunization without calling PDS or checking S flag.
        """
        imms = self.immunization_repo.get_immunization_by_id(imms_id)

        if not imms:
            return None

        try:
            nhs_number = [x for x in imms["contained"] if x["resourceType"] == "Patient"][0]["identifier"][0]["value"]
        except (KeyError, IndexError):
            filtered_immunization = imms
        else:
            patient = self.pds_service.get_patient_details(nhs_number)
            filtered_immunization = handle_s_flag(imms, patient)
        return Immunization.parse_obj(filtered_immunization)

    def create_immunization(self, immunization: dict) -> Immunization:
        try:
            self.validator.validate(immunization)
        except (ValidationError, ValueError, MandatoryError, NotApplicableError) as error:
            raise CustomValidationError(message=str(error)) from error
        patient = self._validate_patient(immunization)

        if "diagnostics" in patient:
            return patient
        imms = self.immunization_repo.create_immunization(immunization, patient)

        return Immunization.parse_obj(imms)

    def update_immunization(self, imms_id: str, immunization: dict) -> tuple[UpdateOutcome, Immunization]:
        if immunization.get("id", imms_id) != imms_id:
            raise InconsistentIdError(imms_id=imms_id)
        immunization["id"] = imms_id

        try:
            self.validator.validate(immunization)
        except (ValidationError, ValueError, MandatoryError, NotApplicableError) as error:
            raise CustomValidationError(message=str(error)) from error

        patient = self._validate_patient(immunization)
        if "diagnostics" in patient:
            return (None, patient)
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

    @staticmethod
    def has_valid_vaccine_type(immunization: dict, vaccine_types: list[str]):
        return get_vaccine_type(immunization) in vaccine_types

    @staticmethod
    def is_valid_date_from(immunization: dict, date_from: datetime.date):
        if date_from is None:
            return True

        occurrence_datetime = get_occurrence_datetime(immunization)
        if occurrence_datetime is None:
            # TODO: Log error if no date.
            return True

        return occurrence_datetime.date() >= date_from

    @staticmethod
    def is_valid_date_to(immunization: dict, date_to: datetime.date):
        if date_to is None:
            return True

        occurrence_datetime = get_occurrence_datetime(immunization)
        if occurrence_datetime is None:
            # TODO: Log error if no date.
            return True

        return occurrence_datetime.date() <= date_to

    @staticmethod
    def process_patient_for_include(patient: dict):
        fields_to_keep = ["id", "resourceType", "identifier", "birthDate"]
        new_patient = {k: v for k, v in patient.items() if k in fields_to_keep}
        return new_patient

    def search_immunizations(
        self,
        nhs_number: str,
        vaccine_types: list[str],
        params: str,
        date_from: datetime.date = parameter_parser.date_from_default,
        date_to: datetime.date = parameter_parser.date_to_default,
    ) -> FhirBundle:
        """find all instances of Immunization(s) for a patient and specified disease type.
        Returns Bundle[Immunization]
        """
        # TODO: VACCINE_TYPE is disease type a mandatory field? (I assumed it is)
        #  i.e. Should we provide a search option for getting Patient's entire imms history?
        if not nhs_number_mod11_check(nhs_number):
            diagnostics_error = create_diagnostics(nhs_number)
            return diagnostics_error
        resources = self.immunization_repo.find_immunizations(nhs_number)
        resources = [
            r
            for r in resources
            # TODO: VACCINE_TYPE Change this implementation to use the vaccine type indexed on creation
            if FhirService.has_valid_vaccine_type(r, vaccine_types)
            and FhirService.is_valid_date_from(r, date_from)
            and FhirService.is_valid_date_to(r, date_to)
        ]
        patient_details = self.pds_service.get_patient_details(nhs_number)
        # To check whether the Superseded NHS number present in PDS
        if patient_details:
            pds_nhs_number = patient_details["identifier"][0]["value"]
            if pds_nhs_number != nhs_number:
                diagnostics_error = create_diagnostics(nhs_number)
                return diagnostics_error
        patient = patient_details if len(resources) > 0 else None
        entries = [
            BundleEntry(
                resource=Immunization.parse_obj(handle_s_flag(imms, patient)),
                search=BundleEntrySearch(mode="match"),
                fullUrl=f"urn:uuid:{imms['id']}",
            )
            for imms in resources
        ]
        if patient:
            entries.append(
                BundleEntry(
                    resource=FhirService.process_patient_for_include(patient), search=BundleEntrySearch(mode="include")
                )
            )
        fhir_bundle = FhirBundle(resourceType="Bundle", type="searchset", entry=entries)
        url = f"{get_service_url()}/Immunization?{params}"
        fhir_bundle.link = [BundleLink(relation="self", url=url)]
        return fhir_bundle

    @timed
    def _validate_patient(self, imms: dict) -> dict:
        """
        Get the NHS number from the contained Patient resource and validate it with PDS.

        If the NHS number doesn't exist, return an empty dict.
        If the NHS number exists, get the patient details from PDS and return the patient details.
        """
        try:
            nhs_number = [x for x in imms["contained"] if x["resourceType"] == "Patient"][0]["identifier"][0]["value"]
        except (KeyError, IndexError):
            nhs_number = None

        if not nhs_number:
            return {}

        patient = self.pds_service.get_patient_details(nhs_number)
        # To check whether the Superseded NHS number present in PDS
        if patient:
            pds_nhs_number = patient["identifier"][0]["value"]
            if pds_nhs_number != nhs_number:
                diagnostics_error = create_diagnostics(nhs_number)
                return diagnostics_error

            return patient

        raise InvalidPatientId(patient_identifier=nhs_number)