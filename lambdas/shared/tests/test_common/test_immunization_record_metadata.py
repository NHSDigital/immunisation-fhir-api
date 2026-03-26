import unittest

from fhir.resources.R4B.identifier import Identifier

from common.models.immunization_record_metadata import ImmunizationRecordMetadata


class TestImmunizationRecordMetadata(unittest.TestCase):
    def test_initialization(self):
        identifier = Identifier.construct(value="12345")

        metadata = ImmunizationRecordMetadata(
            identifier=identifier, resource_version=1, is_deleted=False, is_reinstated=False
        )

        self.assertEqual(metadata.identifier.value, "12345")
        self.assertEqual(metadata.resource_version, 1)
        self.assertFalse(metadata.is_deleted)
        self.assertFalse(metadata.is_reinstated)
