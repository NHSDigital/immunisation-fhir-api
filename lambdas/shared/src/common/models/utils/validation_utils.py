"""Utils for backend folder"""

from fhir.resources.R4B.identifier import Identifier

from common.models.constants import Constants, Urls
from common.models.errors import InconsistentIdentifierError, InconsistentResourceVersionError, MandatoryError
from common.models.field_names import FieldNames
from common.models.obtain_field_value import ObtainFieldValue
from common.models.utils.base_utils import obtain_field_location
from common.redis_client import get_redis_client


def get_target_disease_codes(immunization: dict):
    """Takes a FHIR immunization resource and returns a list of target disease codes"""

    target_disease_codes = []

    # Obtain the target disease element from the immunization resource
    try:
        target_disease = ObtainFieldValue.target_disease(immunization)
    except (KeyError, IndexError) as error:
        raise MandatoryError(
            f"Validation errors: {obtain_field_location(FieldNames.target_disease_codes)} is a mandatory field"
        ) from error

    # For each item in the target disease list, extract the snomed code
    for i, element in enumerate(target_disease):
        try:
            code = [x["code"] for x in element["coding"] if x.get("system") == Urls.snomed][0]
        except (KeyError, IndexError) as error:
            raise MandatoryError(
                f"protocolApplied[0].targetDisease[{i}].coding[?(@.system=='http://snomed.info/sct')].code"
                + " is a mandatory field"
            ) from error

        if code is None:
            raise ValueError(
                f"'None' is not a valid value for '{obtain_field_location(FieldNames.target_disease_codes)}'"
            )

        target_disease_codes.append(code)

    return target_disease_codes


def convert_disease_codes_to_vaccine_type(
    disease_codes_input: list,
) -> str | None:
    """
    Takes a list of disease codes and returns the corresponding vaccine type if found,
    otherwise raises a value error
    """
    key = ":".join(sorted(disease_codes_input))
    vaccine_type = get_redis_client().hget(Constants.DISEASES_TO_VACCINE_TYPE_HASH_KEY, key)

    if not vaccine_type:
        raise ValueError(
            f"Validation errors: protocolApplied[0].targetDisease[*].coding[?(@.system=='{Urls.snomed}')].code"
            f" - {disease_codes_input} is not a valid combination of disease codes for this service"
        )
    return vaccine_type


def get_vaccine_type(immunization: dict):
    """
    Take a FHIR immunization resource and returns the vaccine type based on the combination of target diseases.
    If combination of disease types does not map to a valid vaccine type, a value error is raised
    """
    # Obtain list of target diseases
    try:
        target_diseases = get_target_disease_codes(immunization)
        if not target_diseases:
            raise ValueError
    except MandatoryError as error:
        raise ValueError(str(error)) from error
    except ValueError as error:
        raise ValueError(f"{obtain_field_location(FieldNames.target_disease_codes)} is a mandatory field") from error

    # Convert list of target diseases to vaccine type
    return convert_disease_codes_to_vaccine_type(target_diseases)


def validate_identifiers_match(new_identifier: Identifier, existing_identifier: Identifier) -> None:
    """Checks if the identifier system and values match for a new and existing Identifier. Raises an
    InconsistentIdentifierError if there is a mismatch. Use this function in the Update Imms journey"""

    if new_identifier.system != existing_identifier.system and new_identifier.value != existing_identifier.value:
        raise InconsistentIdentifierError(
            "Validation errors: identifier[0].system and identifier[0].value doesn't match with the stored content"
        )

    if new_identifier.system != existing_identifier.system:
        raise InconsistentIdentifierError(
            "Validation errors: identifier[0].system doesn't match with the stored content"
        )

    if new_identifier.value != existing_identifier.value:
        raise InconsistentIdentifierError("Validation errors: identifier[0].value doesn't match with the stored content")

    return None


def validate_resource_versions_match(
    resource_version_in_request: int, actual_resource_version: int, imms_id: str
) -> None:
    """Checks if the resource version in the request and the resource version of the actual Immunization record matches.
    Raises a InconsistentResourceVersion if they do not match."""
    if actual_resource_version > resource_version_in_request:
        raise InconsistentResourceVersionError(
            f"Validation errors: The requested immunization resource {imms_id} has changed since the last retrieve."
        )

    if actual_resource_version < resource_version_in_request:
        raise InconsistentResourceVersionError(
            f"Validation errors: The requested immunization resource {imms_id} version is inconsistent with the "
            f"existing version."
        )

    return None
