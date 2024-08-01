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
from fhir_repository import ImmunizationRepository
from base_utils.base_utils import obtain_field_value
from models.field_names import FieldNames
from models.errors import InvalidPatientId, CustomValidationError, UnhandledResponseError
from models.fhir_immunization import ImmunizationValidator
from models.utils.generic_utils import nhs_number_mod11_check, get_occurrence_datetime, create_diagnostics
from models.constants import Constants
from models.errors import MandatoryError
from models.constants import Constants
from pds_service import PdsService
from s_flag_handler import handle_s_flag
from timer import timed
from filter import Filter


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
    
    def get_immunization_by_identifier(self, identifier_pk: str, imms_vax_type_perms: str) -> Optional[dict]:
        """
        Get an Immunization by its ID. Return None if not found. If the patient doesn't have an NHS number,
        return the Immunization without calling PDS or checking S flag.
        """
        imms_resp = self.immunization_repo.get_immunization_by_identifier(identifier_pk, imms_vax_type_perms)
        if not imms_resp:
            return None
        else:
            return imms_resp
        

    def get_immunization_by_id(self, imms_id: str, imms_vax_type_perms: str) -> Optional[dict]:
        """
        Get an Immunization by its ID. Return None if not found. If the patient doesn't have an NHS number,
        return the Immunization without calling PDS or checking S flag.
        """
        if not (imms_resp := self.immunization_repo.get_immunization_by_id(imms_id, imms_vax_type_perms)):
            return None

        # Remove fields rom the imms resource which are not to be returned for read
        imms_filtered_for_read = Filter.read(imms_resp.get("Resource", {}))

        # Handle s-flag filtering, where applicable
        if not (nhs_number := obtain_field_value(imms_filtered_for_read, FieldNames.patient_identifier_value)):
            imms_filtered_for_read_and_s_flag = imms_filtered_for_read
        else:
            if patient := self.pds_service.get_patient_details(nhs_number):
                imms_filtered_for_read_and_s_flag = handle_s_flag(imms_filtered_for_read, patient)
            else:
                raise UnhandledResponseError("unable to validate NHS number with downstream service")

        return {
            "Version": imms_resp.get("Version", ""),
            "Resource": Immunization.parse_obj(imms_filtered_for_read_and_s_flag),
        }

    def get_immunization_by_id_all(self, imms_id: str, imms: dict) -> Optional[dict]:
        """
        Get an Immunization by its ID. Return None if not found. If the patient doesn't have an NHS number,
        return the Immunization without calling PDS or checking S flag.
        """
        imms["id"] = imms_id
        try:
            self.validator.validate(imms)
            # Initialize errors list
            all_errors = []

            # Check the top-level Immunization resource
            all_errors.extend(check_for_unknown_elements(imms, Constants.allowed_keys_with_id["Immunization"], "Immunization"))

            # Check each contained resource
            for contained_resource in imms.get("contained", []):
                resource_type = contained_resource.get("resourceType")
                all_errors.extend(check_for_unknown_elements(contained_resource, Constants.allowed_keys[resource_type], resource_type))

            # Concatenate errors into a single string separated by semicolons
            error = "; ".join(all_errors)
            if error:
                raise ValueError(error)
        except (ValidationError, ValueError, MandatoryError) as error:
            raise CustomValidationError(message=str(error)) from error
        imms_resp = self.immunization_repo.get_immunization_by_id_all(imms_id, imms)
        return imms_resp

    def create_immunization(self, immunization: dict, imms_vax_type_perms) -> Immunization:
        try:
            self.validator.validate(immunization)
            # Initialize errors list
            all_errors = []

            # Check the top-level Immunization resource
            all_errors.extend(check_for_unknown_elements(immunization, Constants.allowed_keys["Immunization"], "Immunization"))

            # Check each contained resource
            for contained_resource in immunization.get("contained", []):
                resource_type = contained_resource.get("resourceType")
                all_errors.extend(check_for_unknown_elements(contained_resource, Constants.allowed_keys[resource_type], resource_type))

            # Concatenate errors into a single string separated by semicolons
            error = "; ".join(all_errors)
            if error:
                raise ValueError(error)
        except (ValidationError, ValueError, MandatoryError) as error:
            raise CustomValidationError(message=str(error)) from error
        
        patient = self._validate_patient(immunization)

        if "diagnostics" in patient:
            return patient
        imms = self.immunization_repo.create_immunization(immunization, patient, imms_vax_type_perms)

        return Immunization.parse_obj(imms)

    def update_immunization(
        self, imms_id: str, immunization: dict, existing_resource_version: int, imms_vax_type_perms: str
    ) -> tuple[UpdateOutcome, Immunization]:
        immunization["id"] = imms_id

        try:
            self.validator.validate(immunization)
            # Initialize errors list
            all_errors = []

            # Check the top-level Immunization resource
            all_errors.extend(check_for_unknown_elements(immunization, Constants.allowed_keys_with_id["Immunization"], "Immunization"))

            # Check each contained resource
            for contained_resource in immunization.get("contained", []):
                resource_type = contained_resource.get("resourceType")
                if resource_type not in Constants.allowed_contained_resources:
                    all_errors.append(f"resourcetype Practitioner and Patient are only allowed in contained resource for this service")
                else:
                    all_errors.extend(check_for_unknown_elements(contained_resource, Constants.allowed_keys[resource_type], resource_type))

            # Concatenate errors into a single string separated by semicolons
            error = "; ".join(all_errors)
            if error:
                raise ValueError(error)
        except (ValidationError, ValueError, MandatoryError) as error:
            raise CustomValidationError(message=str(error)) from error

        patient = self._validate_patient(immunization)

        if "diagnostics" in patient:
            return (None, patient)
        imms = self.immunization_repo.update_immunization(
            imms_id, immunization, patient, existing_resource_version, imms_vax_type_perms
        )

        return UpdateOutcome.UPDATE, Immunization.parse_obj(imms)

    def reinstate_immunization(
        self, imms_id: str, immunization: dict, existing_resource_version: int, imms_vax_type_perms: str
    ) -> tuple[UpdateOutcome, Immunization]:
        immunization["id"] = imms_id

        patient = self._validate_patient(immunization)

        if "diagnostics" in patient:
            return (None, patient)
        imms = self.immunization_repo.reinstate_immunization(
            imms_id, immunization, patient, existing_resource_version, imms_vax_type_perms
        )

        return UpdateOutcome.UPDATE, Immunization.parse_obj(imms)

    def update_reinstated_immunization(
        self, imms_id: str, immunization: dict, existing_resource_version: int, imms_vax_type_perms: str
    ) -> tuple[UpdateOutcome, Immunization]:
        immunization["id"] = imms_id
        
        patient = self._validate_patient(immunization)

        if "diagnostics" in patient:
            return (None, patient)
        imms = self.immunization_repo.update_reinstated_immunization(
            imms_id, immunization, patient, existing_resource_version, imms_vax_type_perms
        )

        return UpdateOutcome.UPDATE, Immunization.parse_obj(imms)

    def delete_immunization(self, imms_id, imms_vax_type_perms) -> Immunization:
        """
        Delete an Immunization if it exits and return the ID back if successful.
        Exception will be raised if resource didn't exit. Multiple calls to this method won't change
        the record in the database.
        """
        imms = self.immunization_repo.delete_immunization(imms_id, imms_vax_type_perms)
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
        fields_to_keep = ["id", "resourceType", "identifier", "birthDate"]
        new_patient = {k: v for k, v in patient.items() if k in fields_to_keep}

        # Remove unwanted identifier fields
        new_identifiers = []
        for identifier in new_patient["identifier"]:
            identifier_fields_to_keep = ["system", "value"]
            new_identifiers.append({k: v for k, v in identifier.items() if k in identifier_fields_to_keep})
        new_patient["identifier"] = new_identifiers

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
        date_from: datetime.date = parameter_parser.date_from_default,
        date_to: datetime.date = parameter_parser.date_to_default,
    ) -> FhirBundle:
        """
        Finds all instances of Immunization(s) for a specified patient which are for the specified vaccine type(s).
        Bundles the resources with the relevant patient resource and returns the bundle.
        """
        # TODO: is disease type a mandatory field? (I assumed it is)
        #  i.e. Should we provide a search option for getting Patient's entire imms history?
        if not nhs_number_mod11_check(nhs_number):
            return create_diagnostics()

        # Obtain all resources which are for the requested nhs number and vaccine type(s) and within the date range
        resources = [
            r
            for r in self.immunization_repo.find_immunizations(nhs_number, vaccine_types)
            if self.is_valid_date_from(r, date_from) and self.is_valid_date_to(r, date_to)
        ]

        # Check whether the Superseded NHS number present in PDS
        if pds_patient := self.pds_service.get_patient_details(nhs_number):
            if pds_patient["identifier"][0]["value"] != nhs_number:
                return create_diagnostics()

        # Create the patient URN for the fullUrl field.
        # NOTE: This UUID is assigned when a SEARCH request is received and used only for referencing the patient
        # resource from immunisation resources within the bundle. The fullUrl value we are using is a urn (hence the
        # FHIR key name of "fullUrl" is somewhat misleading) which cannot be used to locate any externally stored
        # patient resource. This is as agreed with VDS team for backwards compatibility with Immunisation History API.
        patient_full_url = f"urn:uuid:{str(uuid4())}"

        # Filter and amend the immunization resources for the SEARCH response
        resources_filtered_for_search = [Filter.search(imms, patient_full_url, pds_patient) for imms in resources]

        # Add bundle entries for each of the immunization resources
        entries = [
            BundleEntry(
                resource=Immunization.parse_obj(handle_s_flag(imms, pds_patient)),
                search=BundleEntrySearch(mode="match"),
                fullUrl=f"https://api.service.nhs.uk/immunisation-fhir-api/Immunization/{imms['id']}",
            )
            for imms in resources_filtered_for_search
        ]

        # Add patient resource if there is at least one immunization resource
        if len(resources) > 0:
            entries.append(
                BundleEntry(
                    resource=self.process_patient_for_bundle(pds_patient),
                    search=BundleEntrySearch(mode="include"),
                    fullUrl=patient_full_url,
                )
            )

        # Create the bundle
        fhir_bundle = FhirBundle(resourceType="Bundle", type="searchset", entry=entries)
        fhir_bundle.link = [BundleLink(relation="self", url=self.create_url_for_bundle_link(params, vaccine_types))]

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
                diagnostics_error = create_diagnostics()
                return diagnostics_error

            return patient

        raise InvalidPatientId(patient_identifier=nhs_number)


# Define a function to check for unknown elements
def check_for_unknown_elements(resource, allowed_keys, resource_type):
    errors = []
    for key in resource.keys():
        if key not in allowed_keys:
            errors.append(f"{key} is not an allowed element of the {resource_type} resource for this service")
    return errors
