"""Immunization Record Metadata"""

from dataclasses import dataclass


@dataclass
class ImmunizationRecordMetadata:
    """Simple class to hold data for the Immunization Record Metadata"""

    resource_version: int
    is_deleted: bool
    is_reinstated: bool
