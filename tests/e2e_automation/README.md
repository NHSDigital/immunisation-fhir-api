# End-to-end Automation Tests

This directory contains End-to-end Automation Tests for the Immunisation FHIR API.

## Setting up e2e_automation tests to run locally

1. Follow the instructions in the root level README.md to setup the [dependencies](../../README.md#environment-setup) and create a [virtual environment](../../README.md#setting-up-a-virtual-environment-with-poetry) for this folder (`e2e_automation`).

2. Add values to the .env file.

    For an example of a template .env file, see [.env.example](./.env.example).

    The following values should be added:

    ```
    aws_token_refresh=True
    baseUrl=https://internal-qa.api.service.nhs.uk/immunisation-fhir-api/FHIR/R4
    auth_url=https://internal-qa.api.service.nhs.uk/oauth2-mock/authorize
    token_url=https://internal-qa.api.service.nhs.uk/oauth2-mock/token
    callback_url=https://oauth.pstmn.io/v1/callback
    S3_env=internal-qa
    aws_profile_name={your-profile}
    ```

3. Add login and secret values to the .env file.

    **Please contact the Imms FHIR API Test team to get these values.**

    The following values should be added:

    ```
    username
    scope
    STATUS_API_KEY
    AWS_DOMAIN_NAME
    Postman_Auth_client_Id
    Postman_Auth_client_Secret
    RAVS_client_Id
    RAVS_client_Secret
    MAVIS_client_Id
    MAVIS_client_Secret
    EMIS_client_Id
    EMIS_client_Secret
    SONAR_client_Id
    SONAR_client_Secret
    TPP_client_Id
    TPP_client_Secret
    MEDICUS_client_Id
    MEDICUS_client_Secret
    ```

4. Run `poetry install --no-root` to install dependencies.

5. The `Makefile` in this directory provides the following commands:

- `make test` - run all tests (may take some time)
- `make smoke-test` - run smoke tests only (quicker)
- `make collect-only` - check that all tests are discovered
