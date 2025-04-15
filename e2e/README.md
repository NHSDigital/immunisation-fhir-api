## End-to-end Tests
This directory contains end-to-end tests. Except for certain files, the majority of the tests hit the proxy (Apigee) and assert the response. 

## Setting up e2e tests to run locally

1. Follow the instructions in the root level README.md to setup the [dependencies](../README.md#environment-setup) and create a [virtual environment](../README.md#) for this folder (`e2e`).

2. Install the [get_token] utility provided by Apigee. It is required for authenticating with the Apigee platform. Please make sure you have an Apigee account for non-prod to be able to run these e2e tests.

3. Add the following values in the `.env` file and set the desired PR number. If there is already an `.env` file make sure that you only have the values specified below.
    ```
    APIGEE_USERNAME={your-apigee-email}
    APIGEE_ENVIRONMENT=internal-dev
    PROXY_NAME=immunisation-fhir-api-pr-100
    SERVICE_BASE_PATH=immunisation-fhir-api/FHIR/R4-pr-100
    ```

    There are other environment variables that are used, but these are the minimum amount for running tests locally. Apart from the first 4 items from the table below, you can ignore the rest of them. This will cause a few test failures, but it's safe to ignore them (locally).

    | Name               | Example                                     | Description                                                                                   |
    |--------------------|---------------------------------------------|-----------------------------------------------------------------------------------------------|
    | `APIGEE_USERNAME`    | your-nhs-email@nhs.net                      | Your NHS email address, used to authenticate with Apigee.                                     |
    | `APIGEE_ENVIRONMENT` | internal-dev                                | The Apigee environment you are targeting (e.g., `internal-dev`, `prod`, etc.).                |
    | `PROXY_NAME`         | immunisation-fhir-api-pr-100                | The name of the Apigee proxy you want to target. You can find this in the Apigee UI.          |
    | `SERVICE_BASE_PATH`  | immunisation-fhir-api/FHIR/R4-pr-100        | The base path for the proxy. This can be found in the "Overview" section of the Apigee UI.    |
    | `STATUS_API_KEY`     | secret                                      | Used to test the `_status` endpoint. If not set, that specific test will fail (can be ignored locally). |
    | `AWS_PROFILE`        | apim-dev                                    | Some operations require the AWS CLI. This profile is used for AWS authentication.             |
    | `AWS_DOMAIN_NAME`    | https://pr-100.imms.dev.vds.platform.nhs.uk | The domain pointing to the backend deployment, used for testing mTLS. Can be ignored locally. |


4. If you prefer to skip Terraform initialization, you can configure the `Makefile` to work without it. This step is optional — if Terraform has already been initialized, you can proceed to the next step.

    **Note:** The `Makefile` includes environment variables that are dynamically set when you run its commands. These variables are populated by scripts that retrieve information about AWS resources deployed to the specified environment.

    For local development, you can simplify the setup by modifying the configuration to point directly to resource names, instead of relying on Terraform initialization.
    ```
    APIGEE_ACCESS_TOKEN ?= $(shell export SSO_LOGIN_URL=https://login.apigee.com && eval get_token -u $(APIGEE_USERNAME))
    AWS_DOMAIN_NAME=""
    DYNAMODB_TABLE_NAME=imms-internal-dev-imms-events
    IMMS_DELTA_TABLE_NAME=imms-internal-dev-delta
    AWS_SQS_QUEUE_NAME=imms-internal-dev-delta-dlq
    AWS_SNS_TOPIC_NAME=imms-internal-dev-delta-sns
    ```

5. The `Makefile` in this directory provides commands for running various sets of tests. The most important one for local development is `test-immunization`, which tests each Immunization operation such as create, read, delete, etc. To run all tests, use: `make run`.

## Tests

Each test follows a certain pattern. Each file contains a closely related feature. Each test class bundles related tests for that specific category. The first test is always the happy-path test. For backend operations, this first test, will be executed for each method of authentication i.e. `ApplicationRestricted`, `Cis2` and `NhsLogin`. The docstring in each test method contains a BDD style short summary.

Sending a request to the proxy involves a few steps. First we need to create an Apigee product and then create an Apigee
app associated with that product. This app may need certain custom attributes depending on the authentication method.
All
the steps are put away in `utils/base_test.py` in a parent class. Unless you want to test certain scenarios, generally
the `setUpClass` and `tearDownClass` will set everything up for you.

### Implementation

This section contains information about the implementation. The source code can be put into three categories.

#### test files

Every single file in the parent directory is a test module. See section "Tests" for more info.

#### lib directory

This directory contains everything related to the test setup. The code in this directory has no knowledge of your project.
It doesn't even have the knowledge of the test framework. This is to make it completely stand-alone. You can copy/paste this
directory to another project without changing a line. If you are thinking of adding new functionality to it then keep it
that way.

The content of this directory can be broken down into three categories:

* **apigee:** Everything you need to set up Apigee app, product and authentication
* **authentication:** Contains everything you need to perform proxy authentication. It covers all three types of
  authentication
* **env:** The utilities in the `lib` directory never assumes configurations. You need to pass them directly to create
  an instance of the required tool. The `env.py` file is to make assumptions about the source of the configuration.
  When making changes to this file keep two things in mind. 1- reduce the amount of config by convention over
  configuration
  2- only look for the config when your code actually needs it.

#### utils

The files in this directory are test utilities, but they are still project agnostics. They don't know
anything about your particular project. Think of this directory more like a higher level wrapper around `lib`.
The most important file in this directory is the `base_test.py` file, which contains the test setup and teardown logic
related to common e2e tests.
  
