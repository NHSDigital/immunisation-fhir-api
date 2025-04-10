import unittest
import uuid
from typing import List
from lib.apigee import ApigeeService, ApigeeApp, ApigeeProduct
from lib.authentication import (
    AppRestrictedAuthentication,
    Cis2Authentication,
    LoginUser,
)
from lib.env import (
    get_auth_url,
    get_proxy_name,
    get_service_base_path,
)
from utils.constants import cis2_user
from utils.factories import (
    make_apigee_service,
    make_app_restricted_app,
    make_cis2_app,
    make_apigee_product,
)
from utils.immunisation_api import ImmunisationApi, parse_location
from utils.resource import generate_imms_resource, delete_imms_records


class ImmunizationBaseTest(unittest.TestCase):
    """It provides a set of apps with for each AuthType with full permission"""

    apigee_service: ApigeeService
    product: ApigeeProduct

    # a list of ImmunizationApi for each authentication type
    imms_apis: List[ImmunisationApi]
    # a list of all apps that was created, so we can delete them at the end
    apps: List[ApigeeApp]
    # an ImmunisationApi with default auth-type: ApplicationRestricted
    default_imms_api: ImmunisationApi
    generated_imms_records: List[str]

    # Called once before any test methods in the class are run.
    # The purpose of setUpClass is to prepare shared resources that all tests in the class can use
    @classmethod
    def setUpClass(cls):
        cls.apps = []
        cls.imms_apis = []
        cls.apigee_service = make_apigee_service()
        base_url = get_service_base_path()
        try:
            display_name = f"test-{get_proxy_name()}"
            product_data = ApigeeProduct(
                name=str(uuid.uuid4()),
                displayName=display_name,
                # we only use one single product for all auth types
                # TODO(Cis2_AMB-1733) add scopes for Cis2
                # TODO(NhsLogin_AMB-1923) add scopes for NhsLogin
                scopes=["urn:nhsd:apim:app:level3:immunisation-fhir-api"],
            )
            cls.product = make_apigee_product(cls.apigee_service, product_data)
            cls.apigee_service.add_proxy_to_product(product_name=cls.product.name, proxy_name=get_proxy_name())

            def make_app_data() -> ApigeeApp:
                _app = ApigeeApp(name=str(uuid.uuid4()))
                _app.set_display_name(display_name)
                _app.add_product(cls.product.name)
                return _app

            # ApplicationRestricted
            app_data = make_app_data()
            app_res_app, app_res_cfg = make_app_restricted_app(cls.apigee_service, app_data)
            cls.apps.append(app_res_app)

            app_res_auth = AppRestrictedAuthentication(get_auth_url(), app_res_cfg)

            cls.default_imms_api = ImmunisationApi(base_url, app_res_auth)
            cls.imms_apis.append(cls.default_imms_api)

            # Cis2
            app_data = make_app_data()
            cis2_app, app_res_cfg = make_cis2_app(cls.apigee_service, app_data)
            cls.apps.append(cis2_app)

            cis2_auth = Cis2Authentication(get_auth_url(), app_res_cfg, LoginUser(username=cis2_user))
            cis2_imms_api = ImmunisationApi(base_url, cis2_auth)
            cls.imms_apis.append(cis2_imms_api)

            # NhsLogin
            # TODO(NhsLogin_AMB-1923) create an app for NhsLogin and append it to the cls.apps,
            #  then create ImmunisationApi and append it to cls.imms_apis
        except Exception as e:
            cls.tearDownClass()
            raise e

    # Class method that runs once after all test methods in the class have finished.
    # It is used to clean up resources that were shared across multiple tests
    @classmethod
    def tearDownClass(cls):
        for app in cls.apps:
            cls.apigee_service.delete_application(app.name)
        if hasattr(cls, "product") and cls:
            cls.apigee_service.delete_product(cls.product.name)

    # Runs after each individual test method in a test class.
    # It’s used to clean up resources that were initialized specifically for a single test,
    # such as temporary files or mock objects.
    def tearDown(cls):
        for api_client in cls.imms_apis:
            if api_client.generated_test_records:
                result = delete_imms_records(api_client.generated_test_records)

                if result.get("failure_count", 0) > 0:
                    print(
                        f"[teardown warning] Deleted {result.get('success_count', 0)} records out of "
                        f"{len(api_client.generated_test_records)}, failed to delete {result['failure_count']}"
                    )

                api_client.generated_test_records.clear()

    @staticmethod
    def create_immunization_resource(imms_api: ImmunisationApi, resource: dict = None) -> str:
        """creates an Immunization resource and returns the resource url"""
        imms = resource if resource else generate_imms_resource()
        response = imms_api.create_immunization(imms)
        assert response.status_code == 201, (response.status_code, response.text)
        return parse_location(response.headers["Location"])

    @staticmethod
    def create_a_deleted_immunization_resource(imms_api: ImmunisationApi, resource: dict = None) -> dict:
        """it creates a new Immunization and then delete it, it returns the created imms"""
        imms = resource if resource else generate_imms_resource()
        response = imms_api.create_immunization(imms)
        assert response.status_code == 201, response.text
        imms_id = parse_location(response.headers["Location"])
        response = imms_api.delete_immunization(imms_id)
        assert response.status_code == 204, response.text
        imms["id"] = str(uuid.uuid4())

        return imms

    def assert_operation_outcome(self, response, status_code: int, contains: str = ""):
        body = response.json()
        self.assertEqual(response.status_code, status_code, response.text)
        self.assertEqual(body["resourceType"], "OperationOutcome")
        self.assertTrue(contains in body["issue"][0]["diagnostics"])
