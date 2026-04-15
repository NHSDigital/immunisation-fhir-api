# End-to-end Automation Tests

This directory contains End-to-end Automation Tests for the Immunisation FHIR API.

## Setting up e2e_automation tests to run locally

1. Follow the instructions in the root level README.md to setup the [dependencies](../../README.md#environment-setup) and create a [virtual environment](../../README.md#setting-up-a-virtual-environment-with-poetry) for this folder (`e2e_automation`).
2. Run `poetry install --no-root` to install dependencies.
3. Ensure you are authenticated with AWS in your terminal, using your preferred method.
4. Choose which approach you wish to use: static apps or temporary apps. Temporary apps are the recommended way to go as
   they are spun up and torn down on each test run, therefore requiring fewer env vars and less operational overhead. Skip
   to the relevant section below depending on which approach you are going to use.

## Setup when using temporary apps

**NOTE:** this approach cannot be used in INT. Both INT and PROD (we do not test here) belong to the APIM Apigee prod
organisation so there is no support for creating apps on the fly.

**Background:** this approach uses the Apigee API to create and teardown applications during a test run. This is the
approach used in the pipeline for all APIM non-prod environments: internal-dev, internal-qa, pr and so forth.

1. Configure your .env file with the required values.

    The [.env.example.dynamic](./.env.example.dynamic) template defines all the values you will need and explains how
    to obtain them. Most will be simple enough, based on the environment you wish to test. However, there is the
    `STATUS_API_KEY` which you will need to ask the testers or tech lead for, and `APIGEE_ACCESS_TOKEN` which is outlined
    below.

2. [Install](https://docs.apigee.com/api-platform/system-administration/auth-tools#install) and run the Apigee [get_token](https://docs.apigee.com/api-platform/system-administration/using-gettoken) tool to obtain an access token.
3. Set this value against the `APIGEE_ACCESS_TOKEN` variable in your .env file.
4. Finally, use the Makefile to run your desired suite of tests.

Note: the `get_token` tool is only supported in Linux environments, so if you are using a Windows environment, you will
at least need to run the operation in WSL to obtain the access token.

## Setup when using static apps

**NOTE:** you must use this approach in INT.

1. Configure your .env file with the required values.

    The [.env.example.static](./.env.example.static) template defines all the values you will need and explains how
    to obtain them. A lot more configuration is required as you will need to obtain all the `{Supplier}_client_Id` and
    `{Supplier}_client_Secret` values for the static apps in your target environment.

2. Finally, use the Makefile to run your desired suite of tests.

## Test commands

The `Makefile` in this directory provides the following commands:

- `make test` - run all tests (may take some time)
- `make test-api-full` - run API tests
- `make test-api-smoke` - run API smoke tests only (quicker)
- `make test-batch-full` - run Batch tests
- `make test-batch-smoke` - run Batch smoke tests only (quicker)
- `make test-sandbox` - run lightweight tests for the sandbox i.e. just checks /\_ping and /\_status
- `make collect-only` - check that all tests are discovered

If you want even more granular control, you can run `poetry run pytest features -m` followed by the given suite you
want to run e.g. `Delete_Feature`, `Create_Batch_Feature` and so on.
