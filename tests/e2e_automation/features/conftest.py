import os
from pathlib import Path

import allure
import pytest
from dotenv import load_dotenv
from src.dynamoDB.dynamo_db_helper import cleanup_failed_audit_records_for_filename
from utilities.api_fhir_immunization_helper import (
    empty_folder,
    get_response_body_for_display,
)
from utilities.api_gen_token import get_tokens
from utilities.api_get_header import get_delete_url_header
from utilities.apigee.apigee_env_helpers import use_temp_apigee_apps
from utilities.apigee.ApigeeApp import ApigeeApp
from utilities.apigee.ApigeeOnDemandAppManager import ApigeeOnDemandAppManager
from utilities.aws_token import refresh_sso_token, set_aws_session_token
from utilities.context import ScenarioContext
from utilities.enums import SupplierNameWithODSCode
from utilities.http_requests_session import http_requests_session
from utilities.sqs_message_halder import purge_all_queues  # noqa: F403

from features.APITests.steps.common_steps import *  # noqa: F403

# Ignore F403 * imports. Pytest BDD requires common steps to be imported in conftest
from features.APITests.steps.common_steps import (
    mns_event_will_be_triggered_with_correct_data_for_deleted_event,  # noqa: F401
)
from features.batchTests.Steps.batch_common_steps import *  # noqa: F403


@pytest.hookimpl(tryfirst=True)
def pytest_bdd_after_step(request, feature, scenario, step, step_func, step_func_args):
    if not step.failed:
        message = f"✅ Step Passed: **{step.name}"
        allure.attach(
            message,
            name=f"Step Passed: {step.name}",
            attachment_type=allure.attachment_type.TEXT,
        )


@pytest.hookimpl(tryfirst=True)
def pytest_bdd_step_error(request, feature, scenario, step, exception):
    message = f"❌ Step failed! **{step.name}** \n Error: {exception}"
    allure.attach(
        message,
        name=f"Step Failed: {step.name}",
        attachment_type=allure.attachment_type.TEXT,
    )


@pytest.hookimpl(tryfirst=True)
def pytest_bdd_before_scenario(request, feature, scenario):
    allure.dynamic.epic("Immunization Service")
    allure.dynamic.suite(feature.name)  # Separates features into distinct suites
    allure.dynamic.feature(feature.name)  # Ensures correct feature grouping
    allure.dynamic.title((scenario.name).replace("_", " "))


@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    empty_folder("output/allure-results")
    empty_folder("output/allure-report")
    load_dotenv()


@pytest.fixture(scope="session")
def global_context():
    aws_profile_name = os.getenv("aws_profile_name")
    (
        refresh_sso_token(aws_profile_name)
        if os.getenv("aws_token_refresh", "false").strip().lower() == "true"
        else set_aws_session_token()
    )

    s3_env = os.getenv("S3_env")
    aws_account_id = os.getenv("aws_account_id")
    mns_validation_required = os.getenv("mns_validation_required", "false").strip().lower() == "true"
    if s3_env and aws_account_id and mns_validation_required:
        purge_all_queues(s3_env, aws_account_id)


@pytest.fixture(scope="session")
def temp_apigee_apps():
    if use_temp_apigee_apps():
        apigee_app_mgr = ApigeeOnDemandAppManager()
        try:
            created_apps = apigee_app_mgr.setup_apps_and_product()
        except Exception as e:
            print(f"[WARN] Apigee on-demand app setup failed — tests requiring dynamic apps will fail individually: {e}")
            yield None
            return

        for test_app in created_apps:
            os.environ[f"{test_app.supplier}_client_Id"] = test_app.client_id
            os.environ[f"{test_app.supplier}_client_Secret"] = test_app.client_secret

        yield created_apps

        apigee_app_mgr.teardown_apps_and_product()
    else:
        yield None


@pytest.fixture
def context(request, global_context, temp_apigee_apps: list[ApigeeApp] | None) -> ScenarioContext:
    ctx = ScenarioContext()
    ctx.aws_profile_name = os.getenv("aws_profile_name")

    node = request.node
    tags = [marker.name for marker in node.own_markers]

    env_vars = [
        "auth_url",
        "token_url",
        "callback_url",
        "baseUrl",
        "username",
        "scope",
        "S3_env",
        "sub_environment",
        "LOCAL_RUN_WITHOUT_S3_UPLOAD",
        "aws_account_id",
        "mns_validation_required",
    ]
    for var in env_vars:
        setattr(ctx, var, os.getenv(var))

    project_root = Path(__file__).resolve().parents[1]
    # Define working_directory at root level
    working_dir = project_root / "batch_files_directory"

    working_dir.mkdir(exist_ok=True)
    ctx.working_directory = str(working_dir)

    for tag in tags:
        if tag.startswith("vaccine_type_"):
            ctx.vaccine_type = tag.split("vaccine_type_")[1]
        if tag.startswith("patient_id_"):
            ctx.patient_id = tag.split("patient_id_")[1]
        if tag.startswith("supplier_name_"):
            ctx.supplier_name = tag.split("supplier_name_")[1]
            get_tokens(ctx, ctx.supplier_name)
            ctx.supplier_name = tag.split("supplier_name_")[1]
            ctx.supplier_ods_code = SupplierNameWithODSCode[ctx.supplier_name].value

    return ctx


def pytest_bdd_after_scenario(request, feature, scenario):
    tags = set(getattr(scenario, "tags", [])) | set(getattr(feature, "tags", []))
    context = request.getfixturevalue("context")
    get_delete_url_header(context)

    if "Delete_cleanUp" in tags:
        if context.ImmsID is not None:
            print(f"\n Delete Request is {context.url}/{context.ImmsID}")
            try:
                context.response = http_requests_session.delete(
                    f"{context.url}/{context.ImmsID}", headers=context.headers
                )
                if context.response.status_code in (401, 403):
                    # Apigee token has expired during a long test session (~13 min run).
                    # The token is scoped per-scenario but the DELETE runs post-scenario.
                    # Log a warning and skip — do NOT assert, as this would report the
                    # teardown expiry as the test failure and mask the actual scenario result.
                    print(
                        f"[TEARDOWN][WARN] DELETE returned {context.response.status_code} for "
                        f"{context.ImmsID} — Apigee token likely expired. Skipping teardown assertion."
                    )
                else:
                    assert context.response.status_code == 204, (
                        f"Expected status code 204, but got {context.response.status_code}. "
                        f"Response: {get_response_body_for_display(context.response)}"
                    )
                    mns_event_will_be_triggered_with_correct_data_for_deleted_event(context)
            except AssertionError:
                raise
            except Exception as e:
                print(f"[TEARDOWN][WARN] Delete cleanup error for {context.ImmsID}: {e}")
        else:
            print("Skipping delete: ImmsID is None")

    if "delete_cleanup_batch" in tags:
        if "IMMS_ID" in context.vaccine_df.columns and context.vaccine_df["IMMS_ID"].notna().any():
            get_tokens(context, context.supplier_name)

            context.vaccine_df["IMMS_ID_CLEAN"] = (
                context.vaccine_df["IMMS_ID"].astype(str).str.replace("Immunization#", "", regex=False)
            )

            for imms_id in context.vaccine_df["IMMS_ID_CLEAN"].dropna().unique():
                delete_url = f"{context.url}/{imms_id}"
                print(f"Sending DELETE request to: {delete_url}")

                response = http_requests_session.delete(delete_url, headers=context.headers)

                if response.status_code != 204:
                    print(
                        f"Cleanup DELETE returned {response.status_code} for {imms_id} (teardown best-effort, not failing test). Response: {get_response_body_for_display(response)}"
                    )
                else:
                    print(f"Deleted {imms_id} successfully.")

            print("Batch cleanup finished.")
        else:
            print(
                " No IMMS_ID column or no values present as test failed due to as exception — skipping delete cleanup."
            )

    # Unconditional audit table cleanup for every batch scenario.
    # This handles the case where the @when archive-wait assert raised before
    # the @then step containing the old inline cleanup call could execute,
    # leaving a "Failed" record inthe next test run's DynamoDB query.
    if hasattr(context, "filename") and context.filename and hasattr(context, "S3_env") and context.S3_env:
        cleanup_failed_audit_records_for_filename(context.filename, context.aws_profile_name, context.S3_env)
