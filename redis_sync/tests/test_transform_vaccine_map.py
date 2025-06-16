''' unit tests for transform_vaccine_map.py '''
import unittest

from transform_vaccine_map import transform_vaccine_map


class TestTransformVaccineMap(unittest.TestCase):
    """Tests for transform_vaccine_map function"""

    def setUp(self):
        """Set up the test environment"""
        self.small_data = {
                "disease": {"d1": {}, "d2": {}, "d3": {}},
                "vaccine": {"v1": {"diseases": ["d1"]},
                            "v2": {"diseases": ["d1", "d3"]},
                            "v3": {"diseases": ["d1", "d2", "d3"]},
                            }
            }

    def test_transform_vaccine_map(self):
        """Test the transform_vaccine_map function"""
        transformed_data = transform_vaccine_map(self.small_data)

        #  check disease d1 has 2 vaccines
        self.assertIn("vaccines", transformed_data["disease"]["d1"])
        self.assertEqual(len(transformed_data["disease"]["d1"]["vaccines"]), 3)
        self.assertIn("v1", transformed_data["disease"]["d1"]["vaccines"])
        self.assertIn("v2", transformed_data["disease"]["d1"]["vaccines"])
        self.assertIn("v3", transformed_data["disease"]["d1"]["vaccines"])
        # check disease d2 has 1 vaccine
        self.assertIn("vaccines", transformed_data["disease"]["d2"])
        self.assertEqual(len(transformed_data["disease"]["d2"]["vaccines"]), 1)
        self.assertIn("v3", transformed_data["disease"]["d2"]["vaccines"])
        # check disease d3 has 1 vaccine
        self.assertIn("vaccines", transformed_data["disease"]["d3"])
        self.assertEqual(len(transformed_data["disease"]["d3"]["vaccines"]), 2)
        self.assertIn("v2", transformed_data["disease"]["d3"]["vaccines"])
        self.assertIn("v3", transformed_data["disease"]["d3"]["vaccines"])
