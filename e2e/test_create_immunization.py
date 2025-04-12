import unittest
from utils.base_test import ImmunizationBaseTest
from utils.constants import env_internal_dev


@unittest.skipIf(env_internal_dev, "TestCreateImmunization for internal-dev environment")
class TestCreateImmunization(ImmunizationBaseTest):

    def test_create_imms(self):
        print("Testing create immunization...")
