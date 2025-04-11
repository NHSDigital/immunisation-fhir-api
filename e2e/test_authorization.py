import unittest

from lib.apigee import ApigeeApp
from utils.base_test import ImmunizationBaseTest
from utils.immunisation_api import ImmunisationApi
from utils.constants import env_internal_dev


@unittest.skipIf(env_internal_dev, "TestApplicationRestrictedAuthorization for internal-dev environment")
class TestApplicationRestrictedAuthorization(ImmunizationBaseTest):

    my_app: ApigeeApp
    my_imms_api: ImmunisationApi

    def tearDown(self):
        print("Tearing down test environment...")

    def test_get_imms_authorised(self):
        print("Testing get immunization authorized...")


@unittest.skipIf(env_internal_dev, "TestCis2Authorization for internal-dev environment")
class TestCis2Authorization(ImmunizationBaseTest):

    def test_get_imms_authorised(self):
        print("Testing get immunization authorized...")
