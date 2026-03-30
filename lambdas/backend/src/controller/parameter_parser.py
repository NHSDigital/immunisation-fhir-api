import datetime
import json
import logging
from dataclasses import dataclass, field

from common.models.constants import RedisHashKeys, Urls
from common.models.utils.generic_utils import nhs_number_mod11_check
from common.redis_client import get_redis_client
from controller.constants import IdentifierSearchElement, IdentifierSearchParameterName, ImmunizationSearchParameterName
from models.errors import ParameterExceptionError

DUPLICATED_PARAMETERS_ERROR_MESSAGE = 'Parameters may not be duplicated. Use commas for "or".'
INVALID_IDENTIFIER_ERROR_MESSAGE = (
    'Search parameter identifier must have one value and must be in the format of "iden'
    'tifier.system|identifier.value" "http://xyz.org/vaccs|2345-gh3s-r53h7-12ny"'
)
NO_PARAMETERS_ERROR_MESSAGE = (
    f"No parameter provided. Search using either {IdentifierSearchParameterName.IDENTIFIER} or "
    f"{ImmunizationSearchParameterName.PATIENT_IDENTIFIER}"
)
TARGET_DISEASE_MUTUAL_EXCLUSIVITY_ERROR = (
    f"Search parameter {ImmunizationSearchParameterName.TARGET_DISEASE} cannot be used with "
    f"{ImmunizationSearchParameterName.IMMUNIZATION_TARGET} or {IdentifierSearchParameterName.IDENTIFIER}. "
    "Use one search type only."
)
TARGET_DISEASE_FORMAT_ERROR = (
    f"Search parameter {ImmunizationSearchParameterName.TARGET_DISEASE} must be in the format "
    f'"{Urls.SNOMED}|{{SNOMED code}}" e.g. "{Urls.SNOMED}|14189004"'
)
TARGET_DISEASE_ALL_INVALID_ERROR = (
    f"Search parameter {ImmunizationSearchParameterName.TARGET_DISEASE} must be one or more valid SNOMED codes "
    "from the supported target disease list."
)

PATIENT_IDENTIFIER_SYSTEM = "https://fhir.nhs.uk/Id/nhs-number"

TARGET_DISEASE_CODES_FIELD = "codes"

TARGET_DISEASE_STATUS_VALID = "valid"
TARGET_DISEASE_STATUS_FORMAT_INVALID = "format_invalid"
TARGET_DISEASE_STATUS_UNMAPPED = "unmapped"

logger = logging.getLogger(__name__)


@dataclass
class SearchParams:
    patient_identifier: str
    immunization_targets: set[str]
    date_from: datetime.date | None
    date_to: datetime.date | None
    include: str | None
    target_disease_codes_for_url: set[str] | None = None

    def __repr__(self):
        return str(self.__dict__)


@dataclass
class SearchParamsResult:
    params: SearchParams
    invalid_immunization_targets: list[str] = field(default_factory=list)
    invalid_target_diseases: list[str] = field(default_factory=list)
    no_mapped_target_diseases_provided: bool = field(default=False)


def process_patient_identifier(identifier_params: dict[str, list[str]]) -> str:
    """Validate and parse patient identifier parameter.

    :raises ParameterExceptionError:
    """
    patient_identifiers = identifier_params.get(ImmunizationSearchParameterName.PATIENT_IDENTIFIER, [])

    if len(patient_identifiers) != 1:
        raise ParameterExceptionError(
            f"Search parameter {ImmunizationSearchParameterName.PATIENT_IDENTIFIER} must have one value."
        )

    patient_identifier_parts = patient_identifiers[0].split("|")
    identifier_system = patient_identifier_parts[0]

    if len(patient_identifier_parts) != 2 or identifier_system != PATIENT_IDENTIFIER_SYSTEM:
        raise ParameterExceptionError(
            "patient.identifier must be in the format of "
            f'"{PATIENT_IDENTIFIER_SYSTEM}|{{NHS number}}" '
            f'e.g. "{PATIENT_IDENTIFIER_SYSTEM}|9000000009"'
        )

    nhs_number = patient_identifier_parts[1]

    if not nhs_number_mod11_check(nhs_number):
        raise ParameterExceptionError(
            f"Search parameter {ImmunizationSearchParameterName.PATIENT_IDENTIFIER} must be a valid NHS number."
        )

    return nhs_number


def process_immunization_target(imms_params: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    """Validate and parse immunization target parameter. Returns (valid_vaccine_types, invalid_vaccine_types).
    Raises ParameterExceptionError only when no values provided or all values are invalid.
    """
    vaccine_types = [
        vaccine_type
        for vaccine_type in set(imms_params.get(ImmunizationSearchParameterName.IMMUNIZATION_TARGET, []))
        if vaccine_type is not None
    ]

    if len(vaccine_types) < 1:
        raise ParameterExceptionError(
            f"Search parameter {ImmunizationSearchParameterName.IMMUNIZATION_TARGET} must have one or more values."
        )

    valid_vaccine_types_set = set(get_redis_client().hkeys(RedisHashKeys.VACCINE_TYPE_TO_DISEASES_HASH_KEY))
    valid = [v for v in vaccine_types if v in valid_vaccine_types_set]
    invalid = [v for v in vaccine_types if v not in valid_vaccine_types_set]

    if not valid:
        raise ParameterExceptionError(
            f"{ImmunizationSearchParameterName.IMMUNIZATION_TARGET} must be one or more of the following: "
            f"{', '.join(sorted(valid_vaccine_types_set))}"
        )

    return valid, invalid


def validate_search_param_mutual_exclusivity(params: dict[str, list[str]]) -> None:
    """Raises ParameterExceptionError if target-disease is used with -immunization.target or identifier."""
    if ImmunizationSearchParameterName.TARGET_DISEASE not in params:
        return
    if ImmunizationSearchParameterName.IMMUNIZATION_TARGET in params:
        raise ParameterExceptionError(TARGET_DISEASE_MUTUAL_EXCLUSIVITY_ERROR)
    if IdentifierSearchParameterName.IDENTIFIER in params:
        raise ParameterExceptionError(TARGET_DISEASE_MUTUAL_EXCLUSIVITY_ERROR)


def _extract_target_disease_values(params: dict[str, list[str]]) -> list[str]:
    """Extract and strip target-disease values from params. Raises if empty."""
    values = [
        v.strip() for v in params.get(ImmunizationSearchParameterName.TARGET_DISEASE, []) if v is not None and v.strip()
    ]
    if not values:
        raise ParameterExceptionError(
            f"Search parameter {ImmunizationSearchParameterName.TARGET_DISEASE} must have one or more values."
        )
    return values


def _safe_load_diseases(vacc_type: str, diseases_json) -> list[dict]:
    try:
        diseases = json.loads(diseases_json)
    except (TypeError, json.JSONDecodeError):
        logger.warning("Could not decode diseases mapping for vaccine type '%s'", vacc_type)
        return []

    if not isinstance(diseases, list):
        return []

    return diseases


def _add_vaccine_to_disease_map(
    disease_to_vaccs_map: dict[str, list[str]],
    code: str | None,
    vacc_type: str,
) -> None:
    if not code:
        return

    existing = disease_to_vaccs_map.get(code)
    if existing is None:
        disease_to_vaccs_map[code] = [vacc_type]
    elif vacc_type not in existing:
        existing.append(vacc_type)


def _build_disease_to_vaccs_map(redis) -> dict[str, list[str]]:
    """Build disease code -> vaccine types map from Redis.

    Uses the explicit target-disease-to-vaccines cache where available, and
    augments it from the existing vaccine-type-to-diseases mapping so target-
    disease search remains compatible with current cache contents.
    """
    disease_to_vaccs_map: dict[str, list[str]] = {}

    disease_to_vaccs_raw = redis.hgetall(RedisHashKeys.TARGET_DISEASE_TO_VACCS_KEY) or {}
    for disease_code, raw_json in disease_to_vaccs_raw.items():
        try:
            decoded = json.loads(raw_json)
        except json.JSONDecodeError:
            logger.warning("Could not decode target_disease_to_vaccs mapping for disease code '%s'", disease_code)
            continue
        if isinstance(decoded, list):
            disease_to_vaccs_map[disease_code] = [str(vacc_type) for vacc_type in decoded]

    # Also derive mappings from the existing vaccine-type -> diseases cache so that
    # target-disease search continues to work while the new cache is being rolled out.
    vacc_to_diseases_raw = redis.hgetall(RedisHashKeys.VACCINE_TYPE_TO_DISEASES_HASH_KEY) or {}
    for vacc_type, diseases_json in vacc_to_diseases_raw.items():
        diseases = _safe_load_diseases(vacc_type, diseases_json)
        if not diseases:
            continue

        for disease in diseases:
            code = disease.get("code") if isinstance(disease, dict) else None
            _add_vaccine_to_disease_map(disease_to_vaccs_map, code, vacc_type)

    return disease_to_vaccs_map


def _build_valid_codes_set(redis, disease_to_vaccs_map: dict[str, list[str]]) -> set[str]:
    """Build set of supported SNOMED codes from Redis list and mapping keys."""
    valid_codes_set: set[str] = set()
    codes_json = redis.hget(RedisHashKeys.TARGET_DISEASE_LIST_KEY, TARGET_DISEASE_CODES_FIELD)
    if codes_json:
        decoded = codes_json.decode() if isinstance(codes_json, bytes) else codes_json
        decoded_codes = None
        try:
            decoded_codes = json.loads(decoded)
        except json.JSONDecodeError:
            logger.warning("Could not decode target_disease_list codes from Redis")
        if decoded_codes is not None and isinstance(decoded_codes, list):
            valid_codes_set.update(str(c) for c in decoded_codes)
    valid_codes_set.update(disease_to_vaccs_map.keys())
    return valid_codes_set


def _classify_target_disease_value(raw: str, valid_codes_set: set[str]) -> tuple[str, str | None]:
    """Classify one target-disease value.

    Returns (status, code_or_none) where status is one of:
    - TARGET_DISEASE_STATUS_VALID
    - TARGET_DISEASE_STATUS_FORMAT_INVALID
    - TARGET_DISEASE_STATUS_UNMAPPED
    """
    if "|" not in raw:
        return TARGET_DISEASE_STATUS_FORMAT_INVALID, None
    parts = raw.split("|", 1)
    if len(parts) != 2:
        return TARGET_DISEASE_STATUS_FORMAT_INVALID, None
    system, code = parts[0].strip(), parts[1].strip()
    if system != Urls.SNOMED or not code:
        return TARGET_DISEASE_STATUS_FORMAT_INVALID, None
    if code not in valid_codes_set:
        return TARGET_DISEASE_STATUS_UNMAPPED, code
    return TARGET_DISEASE_STATUS_VALID, code


def _resolve_target_disease_result(
    valid_raw: list[str],
    unmapped_format_valid: list[str],
    format_invalid_count: int,
    total_count: int,
) -> tuple[list[str], bool]:
    """Apply post-processing and raises if needed.

    Returns (final_valid_raw, no_mapped_target_diseases_provided).
    """
    if format_invalid_count == total_count:
        raise ParameterExceptionError(TARGET_DISEASE_ALL_INVALID_ERROR)

    no_mapped_target_diseases_provided = (
        len(valid_raw) == 0 and len(unmapped_format_valid) > 0 and format_invalid_count == 0
    )
    if no_mapped_target_diseases_provided:
        valid_raw = list(unmapped_format_valid)

    if not no_mapped_target_diseases_provided and len(valid_raw) == 0:
        raise ParameterExceptionError(TARGET_DISEASE_ALL_INVALID_ERROR)

    return valid_raw, no_mapped_target_diseases_provided


def process_target_disease(params: dict[str, list[str]]) -> tuple[list[str], set[str], list[str], bool]:
    """Parse target-disease parameter.

    Returns (valid_raw_for_url, vaccine_types, invalid_diagnostics, no_mapped_target_diseases_provided).
    Raises ParameterExceptionError when no values or all format invalid.
    """
    values = _extract_target_disease_values(params)
    redis = get_redis_client()
    disease_to_vaccs_map = _build_disease_to_vaccs_map(redis)
    valid_codes_set = _build_valid_codes_set(redis, disease_to_vaccs_map)

    valid_raw: list[str] = []
    vaccine_types: set[str] = set()
    invalid_diagnostics: list[str] = []
    unmapped_format_valid: list[str] = []
    format_invalid_count = 0

    for raw in values:
        status, code = _classify_target_disease_value(raw, valid_codes_set)
        if status == TARGET_DISEASE_STATUS_FORMAT_INVALID:
            invalid_diagnostics.append(f"Invalid format for '{raw}': {TARGET_DISEASE_FORMAT_ERROR}")
            format_invalid_count += 1
            continue
        if status == TARGET_DISEASE_STATUS_UNMAPPED:
            invalid_diagnostics.append(
                f"Target disease code '{code}' is not a supported target disease in this service."
            )
            unmapped_format_valid.append(raw)
            continue
        valid_raw.append(raw)
        vaccs_list = disease_to_vaccs_map.get(code, [])
        if vaccs_list:
            vaccine_types.update(vaccs_list)
        else:
            logger.warning(
                "Target disease code '%s' is considered supported but has no vaccine-type mapping",
                code,
            )

    valid_raw, no_mapped_target_diseases_provided = _resolve_target_disease_result(
        valid_raw, unmapped_format_valid, format_invalid_count, len(values)
    )
    return valid_raw, vaccine_types, invalid_diagnostics, no_mapped_target_diseases_provided


def process_mandatory_params_by_disease(
    params: dict[str, list[str]],
) -> tuple[str, list[str], set[str], list[str], bool]:
    """For target-disease search.

    Returns (patient_identifier, valid_raw_for_url, vaccine_types, invalid_diagnostics,
    no_mapped_target_diseases_provided).
    """
    patient_identifier = process_patient_identifier(params)
    valid_raw, vaccine_types, invalid_diagnostics, no_mapped_target_diseases_provided = process_target_disease(params)
    return patient_identifier, valid_raw, vaccine_types, invalid_diagnostics, no_mapped_target_diseases_provided


def validate_and_retrieve_search_params_by_disease(params: dict[str, list[str]]) -> SearchParamsResult:
    """Validate and retrieve search parameters for target-disease search."""
    patient_identifier, valid_raw, vaccine_types, invalid_diagnostics, no_mapped_target_diseases_provided = (
        process_mandatory_params_by_disease(params)
    )
    date_from, date_to, include = process_optional_params(params)

    if date_from and date_to and date_from > date_to:
        raise ParameterExceptionError(
            f"Search parameter {ImmunizationSearchParameterName.DATE_FROM} must be before "
            f"{ImmunizationSearchParameterName.DATE_TO}"
        )

    search_params = SearchParams(
        patient_identifier,
        vaccine_types,
        date_from,
        date_to,
        include,
        target_disease_codes_for_url=set(valid_raw) if valid_raw else None,
    )
    return SearchParamsResult(
        params=search_params,
        invalid_target_diseases=invalid_diagnostics,
        no_mapped_target_diseases_provided=no_mapped_target_diseases_provided,
    )


def process_mandatory_params(params: dict[str, list[str]]) -> tuple[str, list[str], list[str]]:
    """Validate mandatory params and return (patient_identifier, valid_vaccine_types, invalid_vaccine_types).
    Raises ParameterExceptionError for any validation error.
    """
    patient_identifier = process_patient_identifier(params)
    vaccine_types, invalid_vaccine_types = process_immunization_target(params)

    return patient_identifier, vaccine_types, invalid_vaccine_types


def process_optional_params(
    params: dict[str, list[str]],
) -> tuple[datetime.date | None, datetime.date | None, str | None]:
    """Parse optional params (date.from, date.to, _include).
    Raises ParameterExceptionError for any validation error.
    """
    errors = []
    include = None
    date_from = None
    date_to = None

    date_froms = params.get(ImmunizationSearchParameterName.DATE_FROM, [])
    date_tos = params.get(ImmunizationSearchParameterName.DATE_TO, [])
    includes = params.get(ImmunizationSearchParameterName.INCLUDE, [])

    if date_froms:
        if len(date_froms) != 1:
            errors.append(f"Search parameter {ImmunizationSearchParameterName.DATE_FROM} may have one value at most.")
        try:
            date_from = datetime.datetime.strptime(date_froms[0], "%Y-%m-%d").date()
        except ValueError:
            errors.append(f"Search parameter {ImmunizationSearchParameterName.DATE_FROM} must be in format: YYYY-MM-DD")

    if date_tos:
        if len(date_tos) != 1:
            errors.append(f"Search parameter {ImmunizationSearchParameterName.DATE_TO} may have one value at most.")
        try:
            date_to = datetime.datetime.strptime(date_tos[0], "%Y-%m-%d").date()
        except ValueError:
            errors.append(f"Search parameter {ImmunizationSearchParameterName.DATE_TO} must be in format: YYYY-MM-DD")

    if includes:
        if includes[0].lower() != "immunization:patient":
            errors.append(
                f"Search parameter {ImmunizationSearchParameterName.INCLUDE} may only be "
                f"'Immunization:patient' if provided."
            )
        include = includes[0]

    if errors:
        raise ParameterExceptionError("; ".join(errors))

    return date_from, date_to, include


def validate_and_retrieve_search_params(params: dict[str, list[str]]) -> SearchParamsResult:
    """Validate and retrieve search parameters.
    :raises ParameterExceptionError:
    """
    patient_identifier, vaccine_types, invalid_vaccine_types = process_mandatory_params(params)
    date_from, date_to, include = process_optional_params(params)

    if date_from and date_to and date_from > date_to:
        raise ParameterExceptionError(
            f"Search parameter {ImmunizationSearchParameterName.DATE_FROM} must be before "
            f"{ImmunizationSearchParameterName.DATE_TO}"
        )

    search_params = SearchParams(patient_identifier, set(vaccine_types), date_from, date_to, include)
    return SearchParamsResult(params=search_params, invalid_immunization_targets=invalid_vaccine_types)


def parse_search_params(search_params_in_req: dict[str, list[str]]) -> dict[str, list[str]]:
    """Ensures the search params provided in the event do not contain duplicated keys. Will split the parameters
    provided by comma separators. Raises a ParameterExceptionError for duplicated keys. Existing business logic stipulated
    that the API only accepts comma separated values rather than multi-value."""

    if any(len(values) > 1 for values in search_params_in_req.values()):
        raise ParameterExceptionError(DUPLICATED_PARAMETERS_ERROR_MESSAGE)

    parsed_params = {}

    for key, param_values in search_params_in_req.items():
        if len(param_values) == 0:
            parsed_params[key] = []
            continue

        parsed_params[key] = [param.strip() for param_str in param_values for param in param_str.split(",")]

    if len(parsed_params) == 0:
        raise ParameterExceptionError(message=NO_PARAMETERS_ERROR_MESSAGE)

    return parsed_params


def check_identifier_search_params_contain_no_incorrect_keys(search_params: dict[str, list[str]]) -> bool:
    for patient_vacc_type_search_param in ImmunizationSearchParameterName:
        if patient_vacc_type_search_param in search_params:
            return False

    return True


def check_elements_valid(elements: list[str]) -> bool:
    return set(elements).issubset({IdentifierSearchElement.ID, IdentifierSearchElement.META})


def validate_and_retrieve_identifier_search_params(params: dict[str, list[str]]) -> tuple[str, set[str] | None]:
    contains_no_patient_vacc_type_params = check_identifier_search_params_contain_no_incorrect_keys(params)

    if not contains_no_patient_vacc_type_params:
        if (
            ImmunizationSearchParameterName.PATIENT_IDENTIFIER in params
            and IdentifierSearchParameterName.IDENTIFIER in params
        ):
            raise ParameterExceptionError("Search parameter should have either identifier or patient.identifier")

        raise ParameterExceptionError("Identifier search included patient.identifier search parameters")

    # Would we want to permit searching with multiple identifiers in future?
    identifiers_list = params.get(IdentifierSearchParameterName.IDENTIFIER, [])

    if len(identifiers_list) > 1:
        raise ParameterExceptionError(INVALID_IDENTIFIER_ERROR_MESSAGE)

    identifier = identifiers_list[0] if identifiers_list else None
    elements = params.get(IdentifierSearchParameterName.ELEMENTS)

    if not identifier:
        if elements is not None:
            raise ParameterExceptionError("Search parameter _elements must have the following parameter: identifier")

        raise ParameterExceptionError(INVALID_IDENTIFIER_ERROR_MESSAGE)

    if "|" not in identifier or " " in identifier:
        raise ParameterExceptionError(INVALID_IDENTIFIER_ERROR_MESSAGE)

    if not elements:
        return identifier, None

    if not check_elements_valid(elements):
        raise ParameterExceptionError("_elements must be one or more of the following: id,meta")

    return identifier, set(elements)
