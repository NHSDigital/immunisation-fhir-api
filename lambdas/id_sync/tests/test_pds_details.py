import unittest

from pds_details import get_nhs_number_from_pds_resource


class TestGetNhsNumber(unittest.TestCase):
    def test_get_nhs_number_from_pds_resource(self):
        """Test that the NHS Number is retrieved from a full PDS patient resource."""
        mock_pds_resource = {
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": "123456789012",
                }
            ]
        }

        result = get_nhs_number_from_pds_resource(mock_pds_resource)

        self.assertEqual(result, "123456789012")
