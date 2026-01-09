"""Immunization Record Metadata"""

from dataclasses import dataclass

from fhir.resources.R4B.identifier import Identifier


@dataclass
class ImmunizationRecordMetadata:
    """Simple data class for the Immunization Record Metadata"""

    identifier: Identifier
    resource_version: int
    is_deleted: bool
    is_reinstated: bool
