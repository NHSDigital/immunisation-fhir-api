import logging
from uuid import uuid4
import datetime
import os
from enum import Enum
from typing import Optional, Union

from fhir.resources.R4B.bundle import (
    Bundle as FhirBundle,
    BundleEntry,
    BundleLink,
    BundleEntrySearch,
)
from fhir.resources.R4B.immunization import Immunization
from pydantic import ValidationError

import parameter_parser
from authorisation.api_operation_code import ApiOperationCode
from authorisation.authoriser import Authoriser
from fhir_repository import ImmunizationRepository
from models.errors import InvalidPatientId, CustomValidationError, UnauthorizedVaxError, ResourceNotFoundError
from models.fhir_immunization import ImmunizationValidator
from models.utils.generic_utils import nhs_number_mod11_check, get_occurrence_datetime, create_diagnostics, form_json, get_contained_patient
from models.errors import MandatoryError
from models.utils.validation_utils import get_vaccine_type
from timer import timed
from filter import Filter

logging.basicConfig(level="INFO")
logger = logging.getLogger()

def get_service_url(service_env: str = None, service_base_path: str = None
 ) -> str:
    service_env: str = service_env if service_env is not None else os.getenv("IMMUNIZATION_ENV", "")
    service_base_path: str = os.getenv("IMMUNIZATION_BASE_PATH")
    
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
        authoriser: Authoriser = Authoriser(),
        validator: ImmunizationValidator = ImmunizationValidator(),
    ):
        self.authoriser = authoriser
        self.immunization_repo = imms_repo
        self.validator = validator

    def get_immunization_by_identifier(
        self, identifier_pk: str, supplier_name: str, identifier: str, element: str
    ) -> Optional[dict]:
        """
        Get an Immunization by its ID. Return None if not found. If the patient doesn't have an NHS number,
        return the Immunization.
        """
        base_url = f"{get_service_url()}/Immunization"
        imms_resp, vaccination_type = self.immunization_repo.get_immunization_by_identifier(identifier_pk)

        if not imms_resp:
            return form_json(imms_resp, None, None, base_url)

        if not self.authoriser.authorise(supplier_name, ApiOperationCode.SEARCH, {vaccination_type}):
            raise UnauthorizedVaxError()

        patient_full_url = f"urn:uuid:{str(uuid4())}"
        filtered_resource = Filter.search(imms_resp['resource'], patient_full_url)
        imms_resp['resource'] = filtered_resource
        return form_json(imms_resp, element, identifier, base_url)

    def get_immunization_by_id(self, imms_id: str, supplier_system: str) -> Optional[dict]:
        """
        Get an Immunization by its ID. Return None if it is not found. If the patient doesn't have an NHS number,
        return the Immunization.
        """
        if not (imms_resp := self.immunization_repo.get_immunization_by_id(imms_id)):
            return None

        # Returns the Immunisation full resource with no obfuscation
        resource = imms_resp.get("Resource", {})
        vaccination_type = get_vaccine_type(resource)

        if not self.authoriser.authorise(supplier_system, ApiOperationCode.READ, {vaccination_type}):
            raise UnauthorizedVaxError()

        return {
            "Version": imms_resp.get("Version", ""),
            "Resource": Immunization.parse_obj(resource),
        }

    def get_immunization_by_id_all(self, imms_id: str, imms: dict) -> Optional[dict]:
        """
        Get an Immunization by its ID. Return None if not found. If the patient doesn't have an NHS number,
        return the Immunization.
        """
        imms["id"] = imms_id
        try:
            self.validator.validate(imms)
        except (ValidationError, ValueError, MandatoryError) as error:
            raise CustomValidationError(message=str(error)) from error
        imms_resp = self.immunization_repo.get_immunization_by_id_all(imms_id, imms)
        return imms_resp

    def create_immunization(self, immunization: dict, supplier_system: str) -> dict | Immunization:
        if immunization.get("id") is not None:
            raise CustomValidationError("id field must not be present for CREATE operation")

        try:
            self.validator.validate(immunization)
        except (ValidationError, ValueError, MandatoryError) as error:
            raise CustomValidationError(message=str(error)) from error
        patient = self._validate_patient(immunization)

        if "diagnostics" in patient:
            return patient

        vaccination_type = get_vaccine_type(immunization)

        if not self.authoriser.authorise(supplier_system, ApiOperationCode.CREATE, {vaccination_type}):
            raise UnauthorizedVaxError()

        immunisation = self.immunization_repo.create_immunization(immunization, patient, supplier_system)
        return Immunization.parse_obj(immunisation)

    def update_immunization(
        self,
        imms_id: str,
        immunization: dict,
        existing_resource_version: int,
        existing_resource_vacc_type: str,
        supplier_system: str,
    ) -> tuple[Optional[UpdateOutcome], Immunization | dict, Optional[int]]:
        # VED-747 - TODO - this and the below 2 methods are duplicated. We should streamline the update journey
        immunization["id"] = imms_id

        patient = self._validate_patient(immunization)
        if "diagnostics" in patient:
            return None, patient, None

        vaccination_type = get_vaccine_type(immunization)

        # If the user is updating the resource vaccination_type, they must have permissions for both the existing and
        # new type. In most cases it will be the same, but it is possible for users to update the vacc type
        if not self.authoriser.authorise(supplier_system, ApiOperationCode.UPDATE,
                                         {vaccination_type, existing_resource_vacc_type}):
            raise UnauthorizedVaxError()

        imms, updated_version = self.immunization_repo.update_immunization(
            imms_id,
            immunization,
            patient,
            existing_resource_version,
            supplier_system
        )

        return UpdateOutcome.UPDATE, Immunization.parse_obj(imms), updated_version

    def reinstate_immunization(
        self,
        imms_id: str,
        immunization: dict,
        existing_resource_version: int,
        existing_resource_vacc_type: str,
        supplier_system: str,
    ) -> tuple[Optional[UpdateOutcome], Immunization | dict, Optional[int]]:
        immunization["id"] = imms_id
        patient = self._validate_patient(immunization)
        if "diagnostics" in patient:
            return None, patient, None

        vaccination_type = get_vaccine_type(immunization)

        if not self.authoriser.authorise(supplier_system, ApiOperationCode.UPDATE,
                                         {vaccination_type, existing_resource_vacc_type}):
            raise UnauthorizedVaxError()

        imms, updated_version = self.immunization_repo.reinstate_immunization(
            imms_id,
            immunization,
            patient,
            existing_resource_version,
            supplier_system
        )

        return UpdateOutcome.UPDATE, Immunization.parse_obj(imms), updated_version

    def update_reinstated_immunization(
        self,
        imms_id: str,
        immunization: dict,
        existing_resource_version: int,
        existing_resource_vacc_type: str,
        supplier_system: str,
    ) -> tuple[Optional[UpdateOutcome], Immunization | dict, Optional[int]]:
        immunization["id"] = imms_id
        patient = self._validate_patient(immunization)
        if "diagnostics" in patient:
            return None, patient, None

        vaccination_type = get_vaccine_type(immunization)

        if not self.authoriser.authorise(supplier_system, ApiOperationCode.UPDATE,
                                         {vaccination_type, existing_resource_vacc_type}):
            raise UnauthorizedVaxError()

        imms, updated_version = self.immunization_repo.update_reinstated_immunization(
            imms_id,
            immunization,
            patient,
            existing_resource_version,
            supplier_system,
        )

        return UpdateOutcome.UPDATE, Immunization.parse_obj(imms), updated_version

    def delete_immunization(self, imms_id: str, supplier_system: str) -> Immunization:
        """
        Delete an Immunization if it exits and return the ID back if successful.
        Exception will be raised if resource does not exist. Multiple calls to this method won't change
        the record in the database.
        """
        existing_immunisation = self.immunization_repo.get_immunization_by_id(imms_id)

        if not existing_immunisation:
            raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)

        vaccination_type = get_vaccine_type(existing_immunisation.get("Resource", {}))

        if not self.authoriser.authorise(supplier_system, ApiOperationCode.DELETE, {vaccination_type}):
            raise UnauthorizedVaxError()

        imms = self.immunization_repo.delete_immunization(
            imms_id, supplier_system
        )
        return Immunization.parse_obj(imms)

    @staticmethod
    def is_valid_date_from(immunization: dict, date_from: Union[datetime.date, None]):
        """
        Returns False if immunization occurrence is earlier than the date_from, or True otherwise
        (also returns True if date_from is None)
        """
        if date_from is None:
            return True

        if (occurrence_datetime := get_occurrence_datetime(immunization)) is None:
            # TODO: Log error if no date.
            return True

        return occurrence_datetime.date() >= date_from

    @staticmethod
    def is_valid_date_to(immunization: dict, date_to: Union[datetime.date, None]):
        """
        Returns False if immunization occurrence is later than the date_to, or True otherwise
        (also returns True if date_to is None)
        """
        if date_to is None:
            return True

        if (occurrence_datetime := get_occurrence_datetime(immunization)) is None:
            # TODO: Log error if no date.
            return True

        return occurrence_datetime.date() <= date_to

    @staticmethod
    def process_patient_for_bundle(patient: dict):
        """
        Create a patient resource to be returned as part of the bundle by keeping the required fields from the
        patient resource
        """

        # Remove unwanted top-level fields
        fields_to_keep = {"resourceType", "identifier"}
        new_patient = {k: v for k, v in patient.items() if k in fields_to_keep}

        # Remove unwanted identifier fields
        identifier_fields_to_keep = {"system", "value"}
        new_patient["identifier"] = [
            {k: v for k, v in identifier.items() if k in identifier_fields_to_keep}
            for identifier in new_patient.get("identifier", [])
        ]

        if new_patient["identifier"]:
            new_patient["id"] = new_patient["identifier"][0].get("value")

        return new_patient

    @staticmethod
    def create_url_for_bundle_link(params, vaccine_types):
        """
        Updates the immunization.target parameter to include the given vaccine types and returns the url for the search
        bundle.
        """
        base_url = f"{get_service_url()}/Immunization"

        # Update the immunization.target parameter
        new_immunization_target_param = f"immunization.target={','.join(vaccine_types)}"
        parameters = "&".join(
            [new_immunization_target_param if x.startswith("-immunization.target=") else x for x in params.split("&")]
        )

        return f"{base_url}?{parameters}"

    def search_immunizations(
        self,
        nhs_number: str,
        vaccine_types: list[str],
        params: str,
        supplier_system: str,
        date_from: datetime.date = parameter_parser.date_from_default,
        date_to: datetime.date = parameter_parser.date_to_default,
    ) -> tuple[FhirBundle, bool]:
        """
        Finds all instances of Immunization(s) for a specified patient which are for the specified vaccine type(s).
        Bundles the resources with the relevant patient resource and returns the bundle along with a boolean to state
        whether the supplier requested vaccine types they were not authorised for.
        """
        # TODO: is disease type a mandatory field? (I assumed it is)
        #  i.e. Should we provide a search option for getting Patient's entire imms history?
        if not nhs_number_mod11_check(nhs_number):
            return create_diagnostics(), False

        permitted_vacc_types = self.authoriser.filter_permitted_vacc_types(
            supplier_system, ApiOperationCode.SEARCH, set(vaccine_types)
        )

        # Only raise error if supplier's request had no permitted vaccinations
        if not permitted_vacc_types:
            raise UnauthorizedVaxError()

        # Obtain all resources which are for the requested nhs number and vaccine type(s) and within the date range
        resources = [
            r
            for r in self.immunization_repo.find_immunizations(nhs_number, permitted_vacc_types)
            if self.is_valid_date_from(r, date_from) and self.is_valid_date_to(r, date_to)
        ]

        # Create the patient URN for the fullUrl field.
        # NOTE: This UUID is assigned when a SEARCH request is received and used only for referencing the patient
        # resource from immunisation resources within the bundle. The fullUrl value we are using is a urn (hence the
        # FHIR key name of "fullUrl" is somewhat misleading) which cannot be used to locate any externally stored
        # patient resource. This is as agreed with VDS team for backwards compatibility with Immunisation History API.
        patient_full_url = f"urn:uuid:{str(uuid4())}"

        imms_patient_record = get_contained_patient(resources[-1]) if resources else None

        # Filter and amend the immunization resources for the SEARCH response
        resources_filtered_for_search = [Filter.search(imms, patient_full_url) for imms in resources]

        # Add bundle entries for each of the immunization resources
        entries = [
            BundleEntry(
                resource=Immunization.parse_obj(imms),
                search=BundleEntrySearch(mode="match"),
                fullUrl=f"{get_service_url()}/Immunization/{imms['id']}",
            )
            for imms in resources_filtered_for_search
        ]

        # Add patient resource if there is at least one immunization resource
        if len(resources) > 0:
            entries.append(
                BundleEntry(
                    resource=self.process_patient_for_bundle(imms_patient_record),
                    search=BundleEntrySearch(mode="include"),
                    fullUrl=patient_full_url,
                )
            )

        # Create the bundle
        fhir_bundle = FhirBundle(resourceType="Bundle", type="searchset", entry=entries)
        fhir_bundle.link = [BundleLink(
            relation="self",
            url=self.create_url_for_bundle_link(params, permitted_vacc_types)
        )]
        supplier_requested_unauthorised_vaccs = len(vaccine_types) != len(permitted_vacc_types)

        return fhir_bundle, supplier_requested_unauthorised_vaccs

    @timed
    def _validate_patient(self, imms: dict) -> dict:
        """
        Get the NHS number from the contained Patient resource and validate it.

        If the NHS number doesn't exist, return an empty dict.
        If the NHS number exists, check it's valid, and return the patient details.
        """
        try:
            contained_patient = get_contained_patient(imms)
            nhs_number = contained_patient["identifier"][0]["value"]
        except (KeyError, IndexError):
            return {}

        if not nhs_number:
            return {}

        if nhs_number_mod11_check(nhs_number):
            return contained_patient

        raise InvalidPatientId(patient_identifier=nhs_number)
