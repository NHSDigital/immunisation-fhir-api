import uuid
import unittest
from typing import Set

from lib.apigee import ApigeeApp
from lib.authentication import (
    AppRestrictedAuthentication,
    Cis2Authentication,
    LoginUser,
)
from lib.env import get_auth_url, get_proxy_name, get_service_base_path
from utils.authorization import Permission, app_full_access
from utils.base_test import ImmunizationBaseTest
from utils.constants import valid_nhs_number1, cis2_user
from utils.factories import make_app_restricted_app, make_cis2_app
from utils.immunisation_api import ImmunisationApi
from utils.resource import generate_imms_resource
from utils.mappings import VaccineTypes
from utils.constants import env_internal_dev


@unittest.skipIf(env_internal_dev, "TestApplicationRestrictedAuthorization for internal-dev environment")
class TestApplicationRestrictedAuthorization(ImmunizationBaseTest):

    my_app: ApigeeApp
    my_imms_api: ImmunisationApi

    def make_app(self, permissions: Set[Permission], vaxx_type_perms: Set = None):
        # The super class gives us everything we need, which is useful for test setup;
        #  however, we need to create a new app with required permissions.
        #  This new app and its api are called my_app and my_imms_api, i.e., app under test
        display_name = f"test-{get_proxy_name()}"

        app_data = ApigeeApp(name=str(uuid.uuid4()), apiProducts=[self.product.name])
        app_data.set_display_name(display_name)
        self.my_app, app_res_cfg = make_app_restricted_app(self.apigee_service, app_data, permissions, vaxx_type_perms)

        app_res_auth = AppRestrictedAuthentication(get_auth_url(), app_res_cfg)
        base_url = get_service_base_path()

        self.my_imms_api = ImmunisationApi(base_url, app_res_auth)

    def tearDown(self):
        self.apigee_service.delete_application(self.my_app.name)

    def test_get_imms_authorised(self):
        """it should get Immunization if app has immunization:read permission"""
        imms_id = self.create_immunization_resource(self.default_imms_api)
        self.make_app({Permission.READ})
        # When
        response = self.my_imms_api.get_immunization_by_id(imms_id)
        # Then
        self.assertEqual(response.status_code, 200, response.text)

    def test_get_imms_unauthorised(self):
        """it should not get Immunization if app doesn't have immunization:read permission"""
        perms = app_full_access(exclude={Permission.READ})
        self.make_app(perms)
        # When
        response = self.my_imms_api.get_immunization_by_id("id-doesn't-matter", expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)

    def test_create_imms_authorised(self):
        """it should create Immunization if app has immunization:create permission"""
        self.make_app({Permission.CREATE})
        # When
        imms = generate_imms_resource()
        response = self.my_imms_api.create_immunization(imms)
        # Then
        self.assertEqual(response.status_code, 201, response.text)

    def test_create_imms_unauthorised_vaxx(self):
        """it should not create Immunization if app does not have the correct vaccine permission"""
        self.make_app({Permission.CREATE}, {"flu:create"})
        # When
        imms = generate_imms_resource()
        response = self.my_imms_api.create_immunization(imms, expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)

    def test_create_imms_unauthorised(self):
        """it should not create Immunization if app doesn't immunization:create permission"""
        perms = app_full_access(exclude={Permission.CREATE})
        self.make_app(perms)
        # When
        imms = generate_imms_resource()
        result = self.my_imms_api.create_immunization(imms, expected_status_code=403)
        # Then
        self.assertEqual(result.status_code, 403, result.text)

    def test_update_imms_authorised(self):
        """it should update Immunization if app has immunization:update and immunization:create permission"""
        imms = generate_imms_resource()
        imms_id = self.create_immunization_resource(self.default_imms_api, imms)
        imms["id"] = imms_id

        self.make_app({Permission.CREATE, Permission.UPDATE})
        # When
        response = self.my_imms_api.update_immunization(imms_id, imms)
        # Then
        self.assertEqual(response.status_code, 200, response.text)

    def test_update_imms_unauthorised(self):
        """it should not update Immunization if app doesn't immunization:update permission"""
        perms = app_full_access(exclude={Permission.UPDATE})
        self.make_app(perms)
        # When
        response = self.my_imms_api.update_immunization("doesn't-matter", {}, expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)

    def test_update_imms_unauthorised_2(self):
        """it should not update Immunization if app doesn't immunization:create permission"""
        imms = generate_imms_resource()
        imms_id = self.create_immunization_resource(self.default_imms_api, imms)
        imms["id"] = imms_id

        perms = app_full_access(exclude={Permission.CREATE})
        self.make_app(perms)
        # When
        response = self.my_imms_api.update_immunization(imms_id, imms, expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)

    def test_delete_imms_authorised(self):
        """it should delete Immunization if app has immunization:delete permission"""
        imms_id = self.create_immunization_resource(self.default_imms_api)
        self.make_app({Permission.DELETE})
        # When
        response = self.my_imms_api.delete_immunization(imms_id)
        # Then
        self.assertEqual(response.status_code, 204, response.text)

    def test_delete_imms_unauthorised(self):
        """it should not delete Immunization if app doesn't have immunization:delete permission"""
        perms = app_full_access(exclude={Permission.DELETE})
        self.make_app(perms)
        # When
        response = self.my_imms_api.delete_immunization("doesn't-matter", expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)

    def test_search_imms_authorised(self):
        """it should search Immunization if app has immunization:search permission"""
        mmr = generate_imms_resource(valid_nhs_number1, VaccineTypes.mmr)
        _ = self.create_immunization_resource(self.default_imms_api, mmr)

        self.make_app({Permission.SEARCH})
        # When
        response = self.my_imms_api.search_immunizations(valid_nhs_number1, VaccineTypes.mmr)
        # Then
        self.assertEqual(response.status_code, 200, response.text)

    def test_search_imms_unauthorised(self):
        """it should not search Immunization if app doesn't immunization:search permission"""
        perms = app_full_access(exclude={Permission.SEARCH})
        self.make_app(perms)
        # When
        response = self.my_imms_api.search_immunizations(valid_nhs_number1, VaccineTypes.mmr, expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)

    def test_search_imms_unauthorised_vax(self):
        """it should not search Immunization if app does not have proper vax permissions"""
        mmr = generate_imms_resource(valid_nhs_number1, VaccineTypes.mmr)
        _ = self.create_immunization_resource(self.default_imms_api, mmr)

        self.make_app({Permission.SEARCH}, {"flu:read"})
        # When
        response = self.my_imms_api.search_immunizations(valid_nhs_number1, VaccineTypes.mmr, expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)


@unittest.skipIf(env_internal_dev, "TestCis2Authorization for internal-dev environment")
class TestCis2Authorization(ImmunizationBaseTest):
    my_app: ApigeeApp
    my_imms_api: ImmunisationApi

    def make_app(self, permissions: Set[Permission], vaxx_type_perms: Set = None):
        # The super class gives us everything we need, which is useful for test setup;
        #  however, we need to create a new app with required permissions.
        #  This new app and its api are called my_app and my_imms_api, i.e., app under test
        display_name = f"test-{get_proxy_name()}"

        app_data = ApigeeApp(name=str(uuid.uuid4()), apiProducts=[self.product.name])
        app_data.set_display_name(display_name)
        self.my_app, app_res_cfg = make_cis2_app(self.apigee_service, app_data, permissions, vaxx_type_perms)

        app_res_auth = Cis2Authentication(get_auth_url(), app_res_cfg, LoginUser(username=cis2_user))
        base_url = get_service_base_path()

        self.my_imms_api = ImmunisationApi(base_url, app_res_auth)

    def tearDown(self):
        self.apigee_service.delete_application(self.my_app.name)

    def test_get_imms_authorised(self):
        """it should get Immunization if app has immunization:read permission"""
        imms_id = self.create_immunization_resource(self.default_imms_api)
        self.make_app({Permission.READ})
        # When
        response = self.my_imms_api.get_immunization_by_id(imms_id)
        # Then
        self.assertEqual(response.status_code, 200, response.text)

    def test_get_imms_unauthorised(self):
        """it should not get Immunization if app doesn't have immunization:read permission"""
        perms = app_full_access(exclude={Permission.READ})
        self.make_app(perms)
        # When
        response = self.my_imms_api.get_immunization_by_id("id-doesn't-matter", expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)

    def test_get_imms__unauthorised_vaxx(self):
        """it should not get Immunization if app does not have the correct vaccine permission"""
        imms_id = self.create_immunization_resource(self.default_imms_api)
        self.make_app({Permission.READ}, {"flu:create"})
        # When
        response = self.my_imms_api.get_immunization_by_id(imms_id, expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)

    def test_create_imms_authorised(self):
        """it should create Immunization if app has immunization:create permission"""
        self.make_app({Permission.CREATE})
        # When
        imms = generate_imms_resource()
        response = self.my_imms_api.create_immunization(imms)
        # Then
        self.assertEqual(response.status_code, 201, response.text)

    def test_create_imms_unauthorised(self):
        """it should not create Immunization if app doesn't immunization:create permission"""
        perms = app_full_access(exclude={Permission.CREATE})
        self.make_app(perms)
        # When
        imms = generate_imms_resource()
        result = self.my_imms_api.create_immunization(imms, expected_status_code=403)
        # Then
        self.assertEqual(result.status_code, 403, result.text)

    def test_create_imms_unauthorised_vaxx(self):
        """it should not create Immunization if app does not have the correct vaccine permission"""
        self.make_app({Permission.CREATE}, {"flu:create"})
        # When
        imms = generate_imms_resource()
        response = self.my_imms_api.create_immunization(imms, expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)

    def test_update_imms_authorised(self):
        """it should update Immunization if app has the immunization:update and immunization:create permission"""
        imms = generate_imms_resource()
        imms_id = self.create_immunization_resource(self.default_imms_api, imms)
        imms["id"] = imms_id

        self.make_app({Permission.CREATE, Permission.UPDATE})
        # When
        response = self.my_imms_api.update_immunization(imms_id, imms)
        # Then
        self.assertEqual(response.status_code, 200, response.text)

    def test_update_imms_unauthorised(self):
        """it should not update Immunization if app doesn't have the immunization:update permission"""
        perms = app_full_access(exclude={Permission.UPDATE})
        self.make_app(perms)
        # When
        response = self.my_imms_api.update_immunization("doesn't-matter", {}, expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)

    def test_update_imms_unauthorised_vaxx(self):
        """it should not update Immunization if app does not have the correct vaccine permission"""
        imms = generate_imms_resource()
        imms_id = self.create_immunization_resource(self.default_imms_api, imms)
        imms["id"] = imms_id

        self.make_app({Permission.CREATE, Permission.UPDATE}, {"flu:create"})
        # When
        response = self.my_imms_api.update_immunization(imms_id, imms, expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)

    def test_delete_imms_authorised(self):
        """it should delete Immunization if app has immunization:delete permission"""
        imms_id = self.create_immunization_resource(self.default_imms_api)
        self.make_app({Permission.DELETE})
        # When
        response = self.my_imms_api.delete_immunization(imms_id)
        # Then
        self.assertEqual(response.status_code, 204, response.text)

    def test_delete_imms_unauthorised(self):
        """it should not delete Immunization if app doesn't have immunization:delete permission"""
        perms = app_full_access(exclude={Permission.DELETE})
        self.make_app(perms)
        # When
        response = self.my_imms_api.delete_immunization("doesn't-matter", expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)

    def test_delete_imms__unauthorised_vaxx(self):
        """it should not delete Immunization if app does not have the correct vaccine permission"""
        imms_id = self.create_immunization_resource(self.default_imms_api)
        self.make_app({Permission.READ}, {"flu:create"})
        # When
        response = self.my_imms_api.delete_immunization(imms_id, expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)

    def test_search_imms_authorised(self):
        """it should search Immunization if app has immunization:search permission"""
        mmr = generate_imms_resource(valid_nhs_number1, VaccineTypes.mmr)
        _ = self.create_immunization_resource(self.default_imms_api, mmr)

        self.make_app({Permission.SEARCH})
        # When
        response = self.my_imms_api.search_immunizations(valid_nhs_number1, VaccineTypes.mmr)
        # Then
        self.assertEqual(response.status_code, 200, response.text)

    def test_search_imms_unauthorised(self):
        """it should not search Immunization if app doesn't have the immunization:search permission"""
        perms = app_full_access(exclude={Permission.SEARCH})
        self.make_app(perms)
        # When
        response = self.my_imms_api.search_immunizations(valid_nhs_number1, VaccineTypes.mmr, expected_status_code=403)
        # Then
        self.assertEqual(response.status_code, 403, response.text)
