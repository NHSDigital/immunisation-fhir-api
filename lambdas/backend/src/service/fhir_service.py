import copy
import datetime
import logging
import os
import uuid
from typing import Any
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
from common.get_service_url import get_service_url
from common.models.constants import Constants, Urls
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
)
from common.models.utils.validation_utils import (
    get_vaccine_type,
    validate_has_status,
    validate_identifiers_match,
    validate_resource_versions_match,
)
from filter import Filter
from models.errors import UnauthorizedVaxError
from repository.fhir_repository import ImmunizationRepository
from service.search_url_helper import create_url_for_bundle_link

logging.basicConfig(level="INFO")
logger = logging.getLogger()

IMMUNIZATION_BASE_PATH = os.getenv("IMMUNIZATION_BASE_PATH")
IMMUNIZATION_ENV = os.getenv("IMMUNIZATION_ENV")

AUTHORISER = Authoriser()
IMMUNIZATION_VALIDATOR = ImmunizationValidator()


class FhirService:
    _DATA_MISSING_DATE_TIME_ERROR_MSG = (
        "Data quality issue - immunisation with ID %s was found containing no occurrenceDateTime"
    )
    _SINGLE_SNOMED_CODEABLE_CONCEPT_FIELDS = ("site", "route")

    def __init__(
        self,
        imms_repo: ImmunizationRepository,
        authoriser: Authoriser = AUTHORISER,
        validator: ImmunizationValidator = IMMUNIZATION_VALIDATOR,
    ):
        self.authoriser = authoriser
        self.immunization_repo = imms_repo
        self.validator = validator

    @staticmethod
    def _keep_first_snomed_coding(coding: list) -> list:
        snomed_seen = False
        filtered_coding = []
        for coding_entry in coding:
            is_snomed_coding = isinstance(coding_entry, dict) and coding_entry.get("system") == Urls.SNOMED
            if is_snomed_coding and snomed_seen:
                continue

            snomed_seen = snomed_seen or is_snomed_coding
            filtered_coding.append(coding_entry)

        return filtered_coding

    @classmethod
    def _normalize_single_snomed_codeable_concepts(cls, immunization: dict) -> None:
        for field_name in cls._SINGLE_SNOMED_CODEABLE_CONCEPT_FIELDS:
            field = immunization.get(field_name)
            coding = field.get("coding") if isinstance(field, dict) else None
            if isinstance(coding, list):
                field["coding"] = cls._keep_first_snomed_coding(coding)

    def _validate_immunization(self, immunization: dict) -> None:
        immunization_to_validate = copy.deepcopy(immunization)
        self._normalize_single_snomed_codeable_concepts(immunization_to_validate)

        try:
            self.validator.validate(immunization_to_validate)
        except (ValueError, MandatoryError) as error:
            raise CustomValidationError(message=str(error)) from error

    def get_immunization_by_identifier(
        self, identifier: Identifier, supplier_name: str, elements: set[str] | None
    ) -> FhirBundle:
        """
        Get an Immunization by its ID. Returns a FHIR Bundle containing the search results.
        """
        base_url = f"{get_service_url(IMMUNIZATION_ENV, IMMUNIZATION_BASE_PATH)}/Immunization"
        resource, resource_metadata = self.immunization_repo.get_immunization_by_identifier(identifier)

        if not resource:
            return self.make_empty_identifier_search_bundle(base_url)

        vaccination_type = get_vaccine_type(resource)

        if not self.authoriser.authorise(supplier_name, ApiOperationCode.SEARCH, {vaccination_type}):
            raise UnauthorizedVaxError()

        patient_full_url = f"urn:uuid:{str(uuid4())}"
        filtered_resource = Filter.search(resource, patient_full_url)

        return self.make_identifier_search_bundle(
            filtered_resource, resource_metadata.resource_version, elements, identifier, base_url
        )

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

    def create_immunization(self, immunization: dict, supplier_system: str) -> tuple[Id, int]:
        if immunization.get("id") is not None:
            raise CustomValidationError("id field must not be present for CREATE operation")

        self._validate_immunization(immunization)

        vaccination_type = get_vaccine_type(immunization)

        if not self.authoriser.authorise(supplier_system, ApiOperationCode.CREATE, {vaccination_type}):
            raise UnauthorizedVaxError()

        identifier = Identifier.parse_obj(immunization["identifier"][0])
        duplicate_identifier = f"{identifier.system}#{identifier.value}"

        existing_immunization_resource, existing_immunization_meta = (
            self.immunization_repo.get_immunization_by_identifier(identifier)
        )
        if existing_immunization_resource:
            if not existing_immunization_meta.is_deleted:
                raise IdentifierDuplicationError(identifier=duplicate_identifier)

            immunization_id = existing_immunization_resource["id"]
            immunization["id"] = immunization_id
            immunization_fhir_entity = Immunization.parse_obj(immunization)
            updated_version = self.immunization_repo.update_immunization(
                immunization_id,
                immunization_fhir_entity,
                existing_immunization_meta,
                supplier_system,
            )
            return immunization_id, updated_version

        immunization["id"] = str(uuid.uuid4())
        immunization_fhir_entity = Immunization.parse_obj(immunization)

        created_id = self.immunization_repo.create_immunization(immunization_fhir_entity, supplier_system)
        return created_id, 1

    def update_immunization(self, imms_id: str, immunization: dict, supplier_system: str, resource_version: int) -> int:
        self._validate_immunization(immunization)

        immunization_to_update = Immunization.parse_obj(immunization)

        existing_immunization_resource, existing_immunization_meta = (
            self.immunization_repo.get_immunization_resource_and_metadata_by_id(imms_id, include_deleted=True)
        )

        if not existing_immunization_resource:
            raise ResourceNotFoundError(resource_type="Immunization", resource_id=imms_id)

        existing_immunization = Immunization.parse_obj(existing_immunization_resource)

        if not self.authoriser.authorise(
            supplier_system,
            ApiOperationCode.UPDATE,
            {get_vaccine_type(immunization_to_update), get_vaccine_type(existing_immunization)},
        ):
            raise UnauthorizedVaxError()

        validate_identifiers_match(immunization_to_update.identifier[0], existing_immunization_meta.identifier)

        if not existing_immunization_meta.is_deleted:
            validate_resource_versions_match(resource_version, existing_immunization_meta.resource_version, imms_id)

        return self.immunization_repo.update_immunization(
            imms_id, immunization_to_update, existing_immunization_meta, supplier_system
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
        date_from: datetime.date | None,
        date_to: datetime.date | None,
        include: str | None,
        invalid_immunization_targets: list[str] | None = None,
        target_disease_codes_for_url: set[str] | None = None,
        invalid_target_diseases: list[str] | None = None,
    ) -> FhirBundle:
        """
        Finds all instances of Immunization(s) for a specified patient for the given specified vaccine type(s).
        Bundles the resources with the relevant patient resource and returns the bundle along with a boolean to state
        whether the supplier requested vaccine types they were not authorised for.
        When target_disease_codes_for_url is set, the bundle self link uses target-disease param instead of vaccine types.
        """
        permitted_vacc_types = self.authoriser.filter_permitted_vacc_types(
            supplier_system, ApiOperationCode.SEARCH, vaccine_types
        )

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
                fullUrl=f"{get_service_url(IMMUNIZATION_ENV, IMMUNIZATION_BASE_PATH)}/Immunization/{imms['id']}",
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

        if invalid_immunization_targets:
            invalid_list = ", ".join(sorted(invalid_immunization_targets))
            entries.append(
                BundleEntry(
                    resource=OperationOutcome.construct(
                        **create_operation_outcome(
                            resource_id=str(uuid.uuid4()),
                            severity=Severity.warning,
                            code=Code.invalid,
                            diagnostics=f"Your search included invalid -immunization.target value(s) that were ignored: {invalid_list}. The search was performed using the valid value(s) only.",
                        )
                    )
                )
            )

        if invalid_target_diseases:
            for diagnostics in invalid_target_diseases:
                entries.append(
                    BundleEntry(
                        resource=OperationOutcome.construct(
                            **create_operation_outcome(
                                resource_id=str(uuid.uuid4()),
                                severity=Severity.warning,
                                code=Code.invalid,
                                diagnostics=diagnostics,
                            )
                        )
                    )
                )

        bundle_link_url = create_url_for_bundle_link(
            permitted_vacc_types,
            nhs_number,
            date_from,
            date_to,
            include,
            IMMUNIZATION_ENV,
            IMMUNIZATION_BASE_PATH,
            target_disease_codes_for_url=target_disease_codes_for_url,
        )

        return FhirBundle(
            type="searchset",
            entry=entries,
            link=[BundleLink(relation="self", url=bundle_link_url)],
            total=len(processed_resources),
        )

    def make_empty_search_bundle_with_target_disease_not_in_mapping(
        self,
        nhs_number: str,
        date_from: datetime.date | None,
        date_to: datetime.date | None,
        include: str | None,
        target_disease_codes_for_url: set[str] | None = None,
    ) -> FhirBundle:
        entries = [
            BundleEntry(
                resource=OperationOutcome.construct(
                    **create_operation_outcome(
                        resource_id=str(uuid.uuid4()),
                        severity=Severity.warning,
                        code=Code.invalid,
                        diagnostics="This service does not contain any vaccination types with the target disease requested.",
                    )
                )
            )
        ]
        url = create_url_for_bundle_link(
            set(),
            nhs_number,
            date_from,
            date_to,
            include,
            IMMUNIZATION_ENV,
            IMMUNIZATION_BASE_PATH,
            target_disease_codes_for_url=target_disease_codes_for_url or set(),
        )
        return FhirBundle(
            type="searchset",
            entry=entries,
            link=[BundleLink(relation="self", url=url)],
            total=0,
        )

    def _filter_search_results_by_date_and_status(
        self,
        immunizations: list[dict],
        date_from: datetime.date | None,
        date_to: datetime.date | None,
        status: str | None,
    ) -> list[dict]:
        return [
            immunization
            for immunization in immunizations
            if self.is_valid_date_from(immunization, date_from)
            and self.is_valid_date_to(immunization, date_to)
            and validate_has_status(immunization, status)
        ]

    def is_valid_date_from(self, immunization: dict, date_from: datetime.date | None):
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

    def is_valid_date_to(self, immunization: dict, date_to: datetime.date | None):
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
    def make_identifier_search_bundle(
        resource: dict | None,
        version_id: int | None,
        elements: set[str] | None,
        identifier: Identifier,
        base_url: str,
    ) -> FhirBundle:
        searched_url = f"{base_url}?identifier={identifier.system}|{identifier.value}" + (
            f"&_elements={','.join(sorted(elements))}" if elements else ""
        )

        meta = {"versionId": version_id}

        # Full Immunization payload to be returned if only the identifier parameter was provided and truncated when
        # _elements is used
        if elements is not None:
            resource_for_bundle: dict[str, Any] = {"resourceType": "Immunization"}
            if "id" in elements:
                resource_for_bundle["id"] = resource["id"]
            if "meta" in elements:
                resource_for_bundle["meta"] = meta

        else:
            resource_for_bundle = copy.deepcopy(resource)
            resource_for_bundle["meta"] = meta

        entry = BundleEntry.construct(
            fullUrl=f"{base_url}/{resource['id']}",
            resource=(
                Immunization.construct(**resource_for_bundle)
                if elements
                else Immunization.parse_obj(resource_for_bundle)
            ),
            search=BundleEntrySearch.construct(mode="match") if not elements else None,
        )

        return FhirBundle(
            type="searchset",
            link=[BundleLink(relation="self", url=searched_url)],
            entry=[entry],
            total=1,
        )

    @staticmethod
    def make_empty_identifier_search_bundle(base_url: str) -> FhirBundle:
        no_results_url = f"{base_url}?identifier=None"
        return FhirBundle(entry=[], link=[BundleLink(relation="self", url=no_results_url)], type="searchset", total=0)

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
