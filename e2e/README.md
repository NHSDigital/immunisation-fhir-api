## End-to-end Tests
This directory contains end-to-end tests. Except for certain files, the majority of the tests hit the proxy (apigee)
and assert the response. 

### Prerequisites

This is a poetry project. Install dependencies using `poetry install`. The project uses Python 3.8 so make sure
you are using the right version. Depending on what kind of tests you want to run you may need different external
dependencies. Here is a full list:

* Make
* Terraform
* AWS CLI v2

To run all the tests you need to provide a `.env` file. The below table describes each variable:

| Name               | Example                                     | Description                                                                                   |
|--------------------|---------------------------------------------|-----------------------------------------------------------------------------------------------|
| APIGEE_USERNAME    | your-nhs-email@nhs.net                      | this value is needed inorder to authenticate with apigee                                      |
| APIGEE_ENVIRONMENT | internal-dev                                | apigee environment                                                                            |
| PROXY_NAME         | immunisation-fhir-api-pr-100                | this the proxy name that you want to target. You can find it in the apigee ui                 |
| SERVICE_BASE_PATH  | immunisation-fhir-api/FHIR/R4-pr-100        | the base path for the proxy. This value can be found in overview section in the apigee ui     |
| STATUS_API_KEY     | secret                                      | if you don't have this value then _status endpoint test will fail. You can ignore it          |
| AWS_PROFILE        | apim-dev                                    | some operation may need to run aws cli. This value is used for aws authentication             |
| AWS_DOMAIN_NAME    | https://pr-100.imms.dev.vds.platform.nhs.uk | this value points to our backend deployment. We use it to test mTLS. Ignore it in local tests |

There are other environment variables that are used, but these are the minimum amount for running tests locally. Apart
from the first three items, you can ignore the rest of them. This will cause a few test failures, but it's safe to
ignore them

### Run

There is a `Makefile` in this directory that runs different sets of tests. The most important one for local testing is
`test-immunization`. They test each Immunization operation such as create, read, delete, etc. Here is how you can run
all tests.

Given your `.env` file:

```shell
export APIGEE_USERNAME=<your-apigee-email>
export APIGEE_ENVIRONMENT=internal-dev
export PROXY_NAME=immunisation-fhir-api-pr-100
export SERVICE_BASE_PATH=immunisation-fhir-api/FHIR/R4-pr-100
```

You can run all tests using:

```
source .env
poetry run python -m unittest -v -c
```

### Tests

Each test follows a certain pattern. Each file contains a closely related feature. Each test class bundles related tests
for that specific category. The first test is always the happy-path test. For backend operations, this first test, will
be executed for each method of authentication i.e. `ApplicationRestricted`, `Cis2` and `NhsLogin`. The docstring in each
test method contains a BDD style short summary.

Sending a request to the proxy involves a few steps. First we need to create an apigee product and then create an apigee
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

The content of this directory can be break down into three categories:

* **apigee:** Everything you need to set up apigee app, product and authentication
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
  
