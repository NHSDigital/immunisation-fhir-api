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
- `make test-api-full` - run API tests
- `make test-api-smoke` - run API smoke tests only (quicker)
- `make test-batch-full` - run Batch tests
- `make test-batch-smoke` - run Batch smoke tests only (quicker)
- `make collect-only` - check that all tests are discovered

## Running e2e_automation tests against PR environments

The environment variables define a client ID and client secret for each of the Apigee test apps we use in static
environments such as `internal-dev`, `internal-qa` and so on.

However, creating pull requests will spin up a dynamic Apigee proxy and AWS backend which lives for the duration of the PR.
To minimise admin overhead, the automation tests create dynamic applications for the duration of a test run rather than
us having to manually create new apps each time we produce a pull request.

These tests are run seamlessly in the pipeline. But if you are doing some local changes and want to test against your
PR environment, please follow these pre-requisites to get it working:

1. [Install](https://docs.apigee.com/api-platform/system-administration/auth-tools#install) and run the Apigee [get_token](https://docs.apigee.com/api-platform/system-administration/using-gettoken) tool to obtain an access token.
2. Set this value against the `APIGEE_ACCESS_TOKEN` in your .env file.
3. Finally, use the [.env.example.pr](./.env.example.pr) as your baseline for your .env file and fill all of the required values.

Note: the `get_token` tool is only supported in Linux environments, so if you are using a Windows environment, you will
at least need to run the operation in WSL to obtain the access token.
