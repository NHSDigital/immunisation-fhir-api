import datetime
import logging
import os
import uuid
from typing import Optional, Union, cast
from uuid import uuid4

from fhir.resources.R4B.bundle import (
    Bundle as FhirBundle,
)
from fhir.resources.R4B.bundle import (
    BundleEntry,
    BundleEntrySearch,
    BundleLink,
)
from fhir.resources.R4B.fhirtypes import Id
from fhir.resources.R4B.identifier import Identifier
from fhir.resources.R4B.immunization import Immunization

import parameter_parser
from authorisation.api_operation_code import ApiOperationCode
from authorisation.authoriser import Authoriser
from common.models.api_errors import (
    MandatoryError,
    UnauthorizedVaxError,
)
from common.models.errors import (
    CustomValidationError,
    IdentifierDuplicationError,
    ResourceNotFoundError,
)
from common.models.fhir_immunization import ImmunizationValidator
from common.models.utils.generic_utils import (
    form_json,
    get_contained_patient,
    get_occurrence_datetime,
)
from common.models.utils.validation_utils import (
    get_vaccine_type,
    validate_identifiers_match,
    validate_resource_versions_match,
)
from filter import Filter
from repository.fhir_repository import ImmunizationRepository

logging.basicConfig(level="INFO")
logger = logging.getLogger()

IMMUNIZATION_BASE_PATH = os.getenv("IMMUNIZATION_BASE_PATH")
IMMUNIZATION_ENV = os.getenv("IMMUNIZATION_ENV")

AUTHORISER = Authoriser()
IMMUNIZATION_VALIDATOR = ImmunizationValidator()


def get_service_url(
    service_env: str = IMMUNIZATION_ENV,
    service_base_path: str = IMMUNIZATION_BASE_PATH,
) -> str:
    if not service_base_path:
        service_base_path = "immunisation-fhir-api/FHIR/R4"

    non_prod = ["internal-dev", "int", "sandbox"]
    if service_env in non_prod:
        subdomain = f"{service_env}."
    elif service_env == "prod":
        subdomain = ""
    else:
        subdomain = "internal-dev."

    return f"https://{subdomain}api.service.nhs.uk/{service_base_path}"


class FhirService:
    def __init__(
        self,
        imms_repo: ImmunizationRepository,
        authoriser: Authoriser = AUTHORISER,
        validator: ImmunizationValidator = IMMUNIZATION_VALIDATOR,
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
        filtered_resource = Filter.search(imms_resp["resource"], patient_full_url)
        imms_resp["resource"] = filtered_resource
        return form_json(imms_resp, element, identifier, base_url)

    def get_immunization_and_version_by_id(self, imms_id: str, supplier_system: str) -> tuple[Immunization, str]:
        """
        Get an Immunization by its ID. Returns the immunization entity and version number.
        """
        resource, resource_metadata = self.immunization_repo.get_immunization_and_resource_meta_by_id(imms_id)

        if resource is None:
            raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)

        vaccination_type = get_vaccine_type(resource)

        if not self.authoriser.authorise(supplier_system, ApiOperationCode.READ, {vaccination_type}):
            raise UnauthorizedVaxError()

        return Immunization.parse_obj(resource), str(resource_metadata.resource_version)

    def create_immunization(self, immunization: dict, supplier_system: str) -> Id:
        if immunization.get("id") is not None:
            raise CustomValidationError("id field must not be present for CREATE operation")

        try:
            self.validator.validate(immunization)
        except (ValueError, MandatoryError) as error:
            raise CustomValidationError(message=str(error)) from error

        vaccination_type = get_vaccine_type(immunization)

        if not self.authoriser.authorise(supplier_system, ApiOperationCode.CREATE, {vaccination_type}):
            raise UnauthorizedVaxError()

        # Set ID for the requested new record
        immunization["id"] = str(uuid.uuid4())

        immunization_fhir_entity = Immunization.parse_obj(immunization)
        identifier = cast(Identifier, immunization_fhir_entity.identifier[0])

        if self.immunization_repo.check_immunization_identifier_exists(identifier.system, identifier.value):
            raise IdentifierDuplicationError(identifier=f"{identifier.system}#{identifier.value}")

        return self.immunization_repo.create_immunization(immunization_fhir_entity, supplier_system)

    def update_immunization(self, imms_id: str, immunization: dict, supplier_system: str, resource_version: int) -> int:
        try:
            self.validator.validate(immunization)
        except (ValueError, MandatoryError) as error:
            raise CustomValidationError(message=str(error)) from error

        existing_immunization, existing_resource_meta = self.immunization_repo.get_immunization_and_resource_meta_by_id(
            imms_id, include_deleted=True
        )

        if not existing_immunization:
            raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)

        # If the user is updating the resource vaccination_type, they must have permissions for both the existing and
        # new type. In most cases it will be the same, but it is possible for users to update the vacc type
        if not self.authoriser.authorise(
            supplier_system,
            ApiOperationCode.UPDATE,
            {get_vaccine_type(immunization), get_vaccine_type(existing_immunization)},
        ):
            raise UnauthorizedVaxError()

        validate_identifiers_match(immunization, existing_immunization)

        if not existing_resource_meta.is_deleted:
            validate_resource_versions_match(resource_version, existing_resource_meta.resource_version, imms_id)

        return self.immunization_repo.update_immunization(imms_id, immunization, existing_resource_meta, supplier_system)

    def delete_immunization(self, imms_id: str, supplier_system: str) -> None:
        """
        Delete an Immunization if it exists and return the ID back if successful. An exception will be raised if the
        resource does not exist.
        """
        existing_immunisation, _ = self.immunization_repo.get_immunization_and_resource_meta_by_id(imms_id)

        if not existing_immunisation:
            raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)

        vaccination_type = get_vaccine_type(existing_immunisation)

        if not self.authoriser.authorise(supplier_system, ApiOperationCode.DELETE, {vaccination_type}):
            raise UnauthorizedVaxError()

        self.immunization_repo.delete_immunization(imms_id, supplier_system)

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
            [(new_immunization_target_param if x.startswith("-immunization.target=") else x) for x in params.split("&")]
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
        fhir_bundle.link = [
            BundleLink(
                relation="self",
                url=self.create_url_for_bundle_link(params, permitted_vacc_types),
            )
        ]
        supplier_requested_unauthorised_vaccs = len(vaccine_types) != len(permitted_vacc_types)

        return fhir_bundle, supplier_requested_unauthorised_vaccs
