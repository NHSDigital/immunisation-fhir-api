import os
import uuid
from typing import Set

from lib.apigee import ApigeeService, ApigeeConfig, ApigeeApp, ApigeeProduct
from lib.authentication import (
    AppRestrictedCredentials,
    AppRestrictedAuthentication,
    AuthType,
    UserRestrictedCredentials,
)
from lib.env import (
    get_apigee_access_token,
    get_auth_url,
    get_apigee_username,
    get_apigee_env,
    get_default_app_restricted_credentials,
    get_proxy_name,
)
from lib.jwks import JwksData
from utils.authorization import (
    Permission,
    app_full_access,
    make_permissions_attribute,
    make_vaxx_permissions_attribute,
)

JWKS_PATH = f"{os.getcwd()}/.well-known"
PRIVATE_KEY_PATH = f"{os.getcwd()}/.keys"


def make_apigee_service(config: ApigeeConfig = None) -> ApigeeService:
    config = (
        config
        if config
        else ApigeeConfig(
            username=get_apigee_username(),
            access_token=get_apigee_access_token(),
            env=get_apigee_env(),
        )
    )
    return ApigeeService(config)


def make_app_restricted_auth(
    config: AppRestrictedCredentials = None,
) -> AppRestrictedAuthentication:
    """If config is None, then we fall back to the default client configuration from env vars. Useful for Int env"""
    config = config if config else get_default_app_restricted_credentials()
    return AppRestrictedAuthentication(auth_url=get_auth_url(), config=config)


def make_apigee_product(
    apigee: ApigeeService = None, product: ApigeeProduct = None
) -> ApigeeProduct:
    if not apigee:
        apigee = make_apigee_service()
    if not product:
        proxies = [
            f"identity-service-{get_apigee_env()}",
            f"identity-service-mock-{get_apigee_env()}",
        ]
        product = ApigeeProduct(
            name=str(uuid.uuid4()),
            scopes=[
                f"urn:nhsd:apim:app:level3:{get_proxy_name()}",
                f"urn:nhsd:apim:user-nhs-cis2:aal3:{get_proxy_name()}",
            ],
            proxies=proxies,
        )

    resp = apigee.create_product(product)
    return ApigeeProduct.from_dict(resp)


def make_app_restricted_app(
    apigee: ApigeeService = None,
    app: ApigeeApp = None,
    permissions: Set[Permission] = None,
    vaxx_type_perms: Set = None,
) -> (ApigeeApp, AppRestrictedCredentials):
    if not apigee:
        apigee = make_apigee_service()

    use_default_app = app is None
    if use_default_app:
        cred = get_default_app_restricted_credentials()
        stored_app = ApigeeApp(name="default-app")
        return stored_app, cred
    else:
        # We use this prefix for file names. This way we don't create a separate file for each jwks
        key_id_prefix = get_proxy_name()
        # NOTE: adding uuid is important. identity-service caches the key_id so,
        #  this way we know it'll be invalidated each time we create a new jwks
        key_id = f"{key_id_prefix}-{str(uuid.uuid4())}"

        jwks_data = JwksData(key_id)
        jwks_url = jwks_data.get_jwks_url(
            base_url="https://api.service.nhs.uk/mock-jwks"
        )
        app.add_attribute("jwks-resource-url", jwks_url)

        if permissions := permissions or app_full_access():
            k, v = make_permissions_attribute(permissions)
            app.add_attribute(k, v)
        app.add_attribute("AuthenticationType", AuthType.APP_RESTRICTED.value)
        app.add_attribute("SupplierSystem", "Test_App")
        if vaxx_type_perms:
            k, v = make_vaxx_permissions_attribute(vaxx_type_perms)
            app.add_attribute(k, v)
        else:
            app.add_attribute(
                "VaccineTypePermissions",
                "flu:create,covid19:create,mmr:create,hpv:create,covid19:update,flu:read,covid19:read,flu:delete,"
                "covid19:delete,mmr:delete,flu:search,covid19:search,mmr:search,rsv:create,rsv:search,rsv:update,"
                "rsv:read,rsv:delete",
            )

        app.add_product(f"identity-service-{get_apigee_env()}")

        resp = apigee.create_application(app)
        stored_app = ApigeeApp.from_dict(resp)

        credentials = AppRestrictedCredentials(
            client_id=stored_app.get_client_id(),
            kid=key_id,
            private_key_content=jwks_data.private_key,
        )

        return stored_app, credentials


def _make_user_restricted_app(
    auth_type: AuthType,
    apigee: ApigeeService = None,
    app: ApigeeApp = None,
    permissions: Set[Permission] = None,
    vaxx_type_perms: Set = None,
) -> ApigeeApp:
    if not apigee:
        apigee = make_apigee_service()

    use_default_app = app is None
    if use_default_app:
        raise NotImplementedError("Default app for user-restricted is not implemented")
    else:
        if permissions := permissions or app_full_access():
            k, v = make_permissions_attribute(permissions)
            app.add_attribute(k, v)
        app.add_attribute("AuthenticationType", auth_type.value)
        app.add_attribute("SupplierSystem", "Test_App")
        if vaxx_type_perms:
            k, v = make_vaxx_permissions_attribute(vaxx_type_perms)
            app.add_attribute(k, v)
        else:
            app.add_attribute(
                "VaccineTypePermissions",
                "flu:create,covid19:create,mmr:create,hpv:create,covid19:update,flu:read,covid19:read,flu:delete,"
                "covid19:delete,mmr:delete,flu:search,covid19:search,mmr:search,rsv:create,rsv:search,rsv:update,"
                "rsv:read,rsv:delete",
            )
        app.add_product(f"identity-service-{get_apigee_env()}")

        resp = apigee.create_application(app)
        return ApigeeApp.from_dict(resp)


def make_cis2_app(
    apigee: ApigeeService = None,
    app: ApigeeApp = None,
    permissions: Set[Permission] = None,
    vaxx_type_perms: Set = None,
) -> (ApigeeApp, UserRestrictedCredentials):
    stored_app = _make_user_restricted_app(
        AuthType.CIS2, apigee, app, permissions, vaxx_type_perms
    )
    credentials = UserRestrictedCredentials(
        client_id=stored_app.get_client_id(),
        client_secret=stored_app.get_client_secret(),
        callback_url=stored_app.callbackUrl,
    )

    return stored_app, credentials
