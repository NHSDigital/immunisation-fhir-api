import os
import pytest
import allure
import requests
from utilities.aws_token import *
from utilities.api_fhir_immunization_helper import *
from utilities.context import ScenarioContext
from dotenv import load_dotenv
from pathlib import Path
from utilities.api_fhir_immunization_helper import empty_folder
from utilities.api_gen_token import get_tokens
from utilities.api_get_header import get_delete_url_header
from utilities.enums import SupplierNameWithODSCode


@pytest.hookimpl(tryfirst=True)
def pytest_bdd_after_step(request, feature, scenario, step, step_func, step_func_args):
    if not step.failed: 
        message = f"✅ Step Passed: **{step.name}"
        allure.attach(message, name=f"Step Passed: {step.name}", attachment_type=allure.attachment_type.TEXT)

@pytest.hookimpl(tryfirst=True)
def pytest_bdd_step_error(request, feature, scenario, step, exception):
    message = f"❌ Step failed! **{step.name}** \n Error: {exception}"
    allure.attach(message, name=f"Step Failed: {step.name}", attachment_type=allure.attachment_type.TEXT)

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
        refresh_sso_token(aws_profile_name) if os.getenv("aws_token_refresh", "false").strip().lower() == "true" else set_aws_session_token()        


@pytest.fixture
def context(request, global_context) -> ScenarioContext:
    ctx = ScenarioContext()
    ctx.aws_profile_name = os.getenv("aws_profile_name")
    
    node = request.node
    tags = [marker.name for marker in node.own_markers]

    env_vars = ["auth_url", "token_url", "callback_url", "baseUrl", "username", "scope", "S3_env", "LOCAL_RUN_WITHOUT_S3_UPLOAD"]
    for var in env_vars:
        setattr(ctx, var, os.getenv(var))
        
    project_root = Path(__file__).resolve().parents[1] 
    # Define working_directory at root level
    working_dir = project_root / "batch_files_directory"

    working_dir.mkdir(exist_ok=True)
    ctx.working_directory = str(working_dir)

    for tag in tags:
        if tag.startswith('vaccine_type_'):
            ctx.vaccine_type = tag.split('vaccine_type_')[1]
        if tag.startswith('patient_id_'):
            ctx.patient_id = tag.split('patient_id_')[1]
        if tag.startswith('supplier_name_'):
            ctx.supplier_name = tag.split('supplier_name_')[1]           
            get_tokens(ctx, ctx.supplier_name)
            ctx.supplier_name = tag.split('supplier_name_')[1]
            ctx.supplier_ods_code= SupplierNameWithODSCode[ctx.supplier_name].value            
              
    return ctx

def pytest_bdd_after_scenario(request, feature, scenario):
    tags = set(getattr(scenario, 'tags', [])) | set(getattr(feature, 'tags', []))
    context = request.getfixturevalue('context')
    get_delete_url_header(context)
    
    if 'Delete_cleanUp' in tags:
        if context.ImmsID is not None:
            print(f"\n Delete Request is {context.url}/{context.ImmsID}")
            context.response = requests.delete(f"{context.url}/{context.ImmsID}", headers=context.headers)
            assert context.response.status_code == 204, f"Expected status code 204, but got {context.response.status_code}. Response: {context.response.json()}"
        else:
            print("Skipping delete: ImmsID is None")


    if 'delete_cleanup_batch' in tags:
        get_tokens(context, context.supplier_name)
        context.vaccine_df["IMMS_ID_CLEAN"] = context.vaccine_df["IMMS_ID"].astype(str).str.replace("Immunization#", "", regex=False)
        
        for imms_id in context.vaccine_df["IMMS_ID_CLEAN"].dropna().unique():
            delete_url = f"{context.url}/{imms_id}"
            print(f"Sending DELETE request to: {delete_url}")
            response = requests.delete(delete_url, headers=context.headers)

            assert response.status_code == 204, (
                f" Failed to delete {imms_id}: expected 204, got {response.status_code}. "
                f"Response: {response.text}"
            )

        print("✅ All IMMS_IDs deleted successfully.")
