"""Immunization Record Metadata"""

from dataclasses import dataclass


@dataclass
class ImmunizationRecordMetadata:
    """Simple data class for the Immunization Record Metadata"""

    resource_version: int
    is_deleted: bool
    is_reinstated: bool
