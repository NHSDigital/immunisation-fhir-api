"""FHIR Controller constants"""

from enum import StrEnum

SUPPLIER_SYSTEM_HEADER_NAME = "SupplierSystem"
E_TAG_HEADER_NAME = "E-Tag"

SEARCH_USING_POST_PATH = "/Immunization/_search"

# TODO - could create string enum for different parameters
# Once parameter parser is tidier, consider moving it there


class IdentifierSearchParameterName(StrEnum):
    IDENTIFIER = "identifier"
    ELEMENTS = "_elements"


class ImmunizationSearchParameterName(StrEnum):
    PATIENT_IDENTIFIER = "patient.identifier"
    IMMUNIZATION_TARGET = "-immunization.target"
    DATE_FROM = "-date.from"
    DATE_TO = "-date.to"
    INCLUDE = "_include"


class IdentifierSearchElement(StrEnum):
    """Valid elements which can be requested to include in the identifier search response"""

    ID = "id"
    META = "meta"


IMMUNIZATION_TARGET_LEGACY_KEY_NAME = "immunization-target"
