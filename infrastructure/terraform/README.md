# About
The Terraform configuration in this folder is executed in each PR and sets up lambdas associated with the PR. Once the PR is merged, it will be used by the release pipeline to deploy to INT and REF. This is also run by the production release pipeline to deploy the lambdas to the prod blue and green sub environments.

## Environments Structure

Terraform is executed via a `Makefile`.
The environment-specific configuration is structured as follows:

    environments/
    └── <ENVIRONMENT>/ # e.g. dev, int, prod (AWS account name)
        └── <SUB_ENVIRONMENT_DIR> / # e.g. pr, internal-dev
            └── variables.tfvars

The `Makefile` automatically reads the `.env` file to determine the correct `variables.tfvars` file to use, allowing customization of infrastructure for each sub-environment.

## Run locally
1. Create a `.env` file with the following values:
```dotenv
ENVIRONMENT=dev # Target AWS account (e.g., dev, int, prod)
SUB_ENVIRONMENT=pr-123 # Sub-environment (e.g., pr-57, internal-dev)
AWS_REGION=eu-west-2
AWS_PROFILE=your-aws-profile
```
2. Run `make init` to download providers and dependencies
3. Run `make plan` to output plan with the changes that terraform will perform
4. **WARNING**: Run `make apply` only after thoroughly reviewing the plan as this might destroy or modify existing infrastructure

Note: If you switch environment configuration in .env ensure that you run `make init-reconfigure` to reconfigure the backend to prevent migrating the existing state to the new backend.

If you want to apply Terraform to a workspace created by a PR you can set the above SUB_ENVIRONMENT to the `PR-number` and ENVIRONMENT set to `dev`.
E.g. `pr-57`. You can use this to test out changes when tests fail in CI.
