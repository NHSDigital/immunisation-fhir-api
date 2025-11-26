import copy
import datetime
import logging
import os
import urllib.parse
import uuid
from typing import Optional, cast
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
from fhir.resources.R4B.operationoutcome import OperationOutcome

from authorisation.api_operation_code import ApiOperationCode
from authorisation.authoriser import Authoriser
from common.models.constants import Constants
from common.models.errors import (
    Code,
    CustomValidationError,
    IdentifierDuplicationError,
    MandatoryError,
    ResourceNotFoundError,
    Severity,
    create_operation_outcome,
)
from common.models.fhir_immunization import ImmunizationValidator
from common.models.utils.generic_utils import (
    get_contained_patient,
    get_occurrence_datetime,
    make_search_bundle,
)
from common.models.utils.validation_utils import (
    get_vaccine_type,
    validate_has_status,
    validate_identifiers_match,
    validate_resource_versions_match,
)
from controller.constants import IMMUNIZATION_TARGET_LEGACY_KEY_NAME, ImmunizationSearchParameterName
from controller.parameter_parser import PATIENT_IDENTIFIER_SYSTEM
from filter import Filter
from models.errors import UnauthorizedVaxError
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
    _DATA_MISSING_DATE_TIME_ERROR_MSG = (
        "Data quality issue - immunisation with ID %s was found containing no occurrenceDateTime"
    )

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
        self, identifier: Identifier, supplier_name: str, elements: Optional[set[str]]
    ) -> FhirBundle:
        """
        Get an Immunization by its ID. Returns a FHIR Bundle containing the search results.
        """
        base_url = f"{get_service_url()}/Immunization"
        resource, resource_metadata = self.immunization_repo.get_immunization_by_identifier(identifier)

        if not resource:
            return make_search_bundle(resource, None, elements, identifier, base_url)

        vaccination_type = get_vaccine_type(resource)

        if not self.authoriser.authorise(supplier_name, ApiOperationCode.SEARCH, {vaccination_type}):
            raise UnauthorizedVaxError()

        patient_full_url = f"urn:uuid:{str(uuid4())}"
        filtered_resource = Filter.search(resource, patient_full_url)

        return make_search_bundle(filtered_resource, resource_metadata.resource_version, elements, identifier, base_url)

    def get_immunization_and_version_by_id(self, imms_id: str, supplier_system: str) -> tuple[Immunization, str]:
        """
        Get an Immunization by its ID. Returns the immunization entity and version number.
        """
        resource, immunization_metadata = self.immunization_repo.get_immunization_resource_and_metadata_by_id(imms_id)

        if resource is None:
            raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)

        vaccination_type = get_vaccine_type(resource)

        if not self.authoriser.authorise(supplier_system, ApiOperationCode.READ, {vaccination_type}):
            raise UnauthorizedVaxError()

        return Immunization.parse_obj(resource), str(immunization_metadata.resource_version)

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

        existing_immunization_resource, existing_immunization_meta = (
            self.immunization_repo.get_immunization_resource_and_metadata_by_id(imms_id, include_deleted=True)
        )

        if not existing_immunization_resource:
            raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)

        # If the user is updating the resource vaccination_type, they must have permissions for both the existing and
        # new type. In most cases it will be the same, but it is possible for users to update the vacc type
        if not self.authoriser.authorise(
            supplier_system,
            ApiOperationCode.UPDATE,
            {get_vaccine_type(immunization), get_vaccine_type(existing_immunization_resource)},
        ):
            raise UnauthorizedVaxError()

        identifier = Identifier.construct(
            system=immunization["identifier"][0]["system"],
            value=immunization["identifier"][0]["value"],
        )

        validate_identifiers_match(identifier, existing_immunization_meta.identifier)

        if not existing_immunization_meta.is_deleted:
            validate_resource_versions_match(resource_version, existing_immunization_meta.resource_version, imms_id)

        return self.immunization_repo.update_immunization(
            imms_id, immunization, existing_immunization_meta, supplier_system
        )

    def delete_immunization(self, imms_id: str, supplier_system: str) -> None:
        """
        Delete an Immunization if it exists and return the ID back if successful. An exception will be raised if the
        resource does not exist.
        """
        existing_immunisation, _ = self.immunization_repo.get_immunization_resource_and_metadata_by_id(imms_id)

        if not existing_immunisation:
            raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)

        vaccination_type = get_vaccine_type(existing_immunisation)

        if not self.authoriser.authorise(supplier_system, ApiOperationCode.DELETE, {vaccination_type}):
            raise UnauthorizedVaxError()

        self.immunization_repo.delete_immunization(imms_id, supplier_system)

    def search_immunizations(
        self,
        nhs_number: str,
        vaccine_types: set[str],
        supplier_system: str,
        date_from: Optional[datetime.date],
        date_to: Optional[datetime.date],
        include: Optional[str],
    ) -> FhirBundle:
        """
        Finds all instances of Immunization(s) for a specified patient for the given specified vaccine type(s).
        Bundles the resources with the relevant patient resource and returns the bundle along with a boolean to state
        whether the supplier requested vaccine types they were not authorised for.
        """
        permitted_vacc_types = self.authoriser.filter_permitted_vacc_types(
            supplier_system, ApiOperationCode.SEARCH, vaccine_types
        )

        # Only raise error if supplier's request had no permitted vaccinations
        if not permitted_vacc_types:
            raise UnauthorizedVaxError()

        # Have to retrieve first and then inspect resource to filter by date
        all_resources = self.immunization_repo.find_immunizations(nhs_number, permitted_vacc_types)
        filtered_resources = self._filter_search_results_by_date_and_status(
            immunizations=all_resources, date_from=date_from, date_to=date_to, status=Constants.COMPLETED_STATUS
        )

        # Create the patient URN for the fullUrl field.
        # NOTE: This UUID is assigned when a SEARCH request is received and used only for referencing the patient
        # resource from immunisation resources within the bundle. The fullUrl value we are using is a urn (hence the
        # FHIR key name of "fullUrl" is somewhat misleading) which cannot be used to locate any externally stored
        # patient resource. This is as agreed with VDS team for backwards compatibility with Immunisation History API.
        patient_full_url = f"urn:uuid:{str(uuid4())}"

        # Adjust immunization resources for the SEARCH response
        processed_resources = [Filter.search(imms, patient_full_url) for imms in copy.deepcopy(filtered_resources)]
        entries = [
            BundleEntry(
                resource=Immunization.parse_obj(imms),
                search=BundleEntrySearch(mode="match"),
                fullUrl=f"{get_service_url()}/Immunization/{imms['id']}",
            )
            for imms in processed_resources
        ]

        # Add patient resource if there is at least one immunization resource
        if len(processed_resources) > 0:
            imms_patient_record = get_contained_patient(filtered_resources[-1])
            entries.append(
                BundleEntry(
                    resource=self.process_patient_for_bundle(imms_patient_record),
                    search=BundleEntrySearch(mode="include"),
                    fullUrl=patient_full_url,
                )
            )

        if len(vaccine_types) != len(permitted_vacc_types):
            # Include Operation Outcome error in response but still return the vaccs the client was authorised for
            entries.append(
                BundleEntry(
                    resource=OperationOutcome.construct(
                        **create_operation_outcome(
                            resource_id=str(uuid.uuid4()),
                            severity=Severity.warning,
                            code=Code.unauthorized,
                            diagnostics="Your search contains details that you are not authorised to request",
                        )
                    )
                )
            )

        return FhirBundle(
            type="searchset",
            entry=entries,
            link=[
                BundleLink(
                    relation="self",
                    url=self.create_url_for_bundle_link(permitted_vacc_types, nhs_number, date_from, date_to, include),
                )
            ],
            total=len(processed_resources),
        )

    def _filter_search_results_by_date_and_status(
        self,
        immunizations: list[dict],
        date_from: Optional[datetime.date],
        date_to: Optional[datetime.date],
        status: Optional[str],
    ) -> list[dict]:
        return [
            immunization
            for immunization in immunizations
            if self.is_valid_date_from(immunization, date_from)
            and self.is_valid_date_to(immunization, date_to)
            and validate_has_status(immunization, status)
        ]

    def is_valid_date_from(self, immunization: dict, date_from: Optional[datetime.date]):
        """
        Returns False if immunization occurrence is earlier than the date_from, or True otherwise
        (also returns True if date_from is None)
        """
        if date_from is None:
            return True

        if (occurrence_datetime := get_occurrence_datetime(immunization)) is None:
            logger.error(self._DATA_MISSING_DATE_TIME_ERROR_MSG, immunization.get("id"))
            return True

        return occurrence_datetime.date() >= date_from

    def is_valid_date_to(self, immunization: dict, date_to: Optional[datetime.date]):
        """
        Returns False if immunization occurrence is later than the date_to, or True otherwise
        (also returns True if date_to is None)
        """
        if date_to is None:
            return True

        if (occurrence_datetime := get_occurrence_datetime(immunization)) is None:
            logger.error(self._DATA_MISSING_DATE_TIME_ERROR_MSG, immunization.get("id"))
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
    def create_url_for_bundle_link(
        immunization_targets: set[str],
        patient_nhs_number: str,
        date_from: Optional[datetime.date],
        date_to: Optional[datetime.date],
        include: Optional[str],
    ) -> str:
        """Creates url for the searchset Bundle Link."""
        params = {
            # Temporarily maintaining this for backwards compatibility with imms history, but we should remove it
            IMMUNIZATION_TARGET_LEGACY_KEY_NAME: ",".join(immunization_targets),
            ImmunizationSearchParameterName.IMMUNIZATION_TARGET: ",".join(immunization_targets),
            ImmunizationSearchParameterName.PATIENT_IDENTIFIER: f"{PATIENT_IDENTIFIER_SYSTEM}|{patient_nhs_number}",
        }

        if date_from:
            params[ImmunizationSearchParameterName.DATE_FROM] = date_from.isoformat()
        if date_to:
            params[ImmunizationSearchParameterName.DATE_TO] = date_to.isoformat()
        if include:
            params[ImmunizationSearchParameterName.INCLUDE] = include

        query = urllib.parse.urlencode(params)
        return f"{get_service_url()}/Immunization?{query}"
