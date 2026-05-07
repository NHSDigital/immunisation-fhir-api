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

## Lambda Trigger Handoff

The `delta_trigger` and `id_sync_sqs_trigger` event source mappings are managed from `../event_source_mappings` so the main instance plan does not rewrite shared backend state. The deploy workflow applies the main instance first, safely adopts any existing trigger mappings into the dedicated trigger workspace, then plans and applies trigger changes from that workspace.

### First Cutover

The normal backend deploy performs idempotent adoption before it plans trigger changes. Use the `Migrate Event Source Mappings` workflow when you want to perform the handoff separately from a full backend deploy. Select the target `environment` and `sub_environment`, then set `confirm_event_source_mapping_migration` to `true`. The migration workflow imports existing mappings, runs `terraform validate`, saves a dedicated trigger `tfplan` artifact, applies that saved plan, and verifies the final Lambda targets.

Before starting, check for duplicate or stale mappings. Replace the variable values with the shared scope and target sub-environment:

```bash
RESOURCE_SCOPE=preprod
SUB_ENVIRONMENT=int-blue
COUNTERPART_SUB_ENVIRONMENT=int-green

EVENTS_STREAM_ARN="$(aws dynamodb describe-table \
  --table-name "imms-${RESOURCE_SCOPE}-imms-events" \
  --query 'Table.LatestStreamArn' \
  --output text)"

ID_SYNC_QUEUE_URL="$(aws sqs get-queue-url \
  --queue-name "imms-${RESOURCE_SCOPE}-id-sync-queue" \
  --query 'QueueUrl' \
  --output text)"

ID_SYNC_QUEUE_ARN="$(aws sqs get-queue-attributes \
  --queue-url "${ID_SYNC_QUEUE_URL}" \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' \
  --output text)"

aws lambda list-event-source-mappings \
  --event-source-arn "${EVENTS_STREAM_ARN}" \
  --function-name "imms-${SUB_ENVIRONMENT}-delta-lambda"

aws lambda list-event-source-mappings \
  --event-source-arn "${EVENTS_STREAM_ARN}" \
  --function-name "imms-${COUNTERPART_SUB_ENVIRONMENT}-delta-lambda"

aws lambda list-event-source-mappings \
  --event-source-arn "${ID_SYNC_QUEUE_ARN}" \
  --function-name "imms-${SUB_ENVIRONMENT}-id-sync-lambda"

aws lambda list-event-source-mappings \
  --event-source-arn "${ID_SYNC_QUEUE_ARN}" \
  --function-name "imms-${COUNTERPART_SUB_ENVIRONMENT}-id-sync-lambda"
```

### Rollback

If the cutover applies cleanly but the target sub-environment must be rolled back, rerun the migration workflow with the previous active sub-environment selected. The workflow should update the managed mappings back to the previous Lambda targets through a saved trigger plan. Verify the final UUIDs, Lambda ARNs, and states with:

```bash
cd infrastructure/event_source_mappings
make init
make workspace
terraform output delta_trigger_uuid
terraform output delta_trigger_function_arn
terraform output delta_trigger_state
terraform output id_sync_sqs_trigger_uuid
terraform output id_sync_sqs_trigger_function_arn
terraform output id_sync_sqs_trigger_state
make verify
```

### Failed Apply Recovery

If the migration fails after import but before apply, rerun the same migration workflow for the same environment and sub-environment. The import step is idempotent for resources already in state and does not delete AWS mappings.

If verification fails, inspect live AWS mappings before retrying:

```bash
aws lambda get-event-source-mapping --uuid "<mapping-uuid>"
aws lambda list-event-source-mappings --event-source-arn "<event-source-arn>"
```

Do not run `make destroy` for shared blue/green trigger workspaces unless this is a controlled teardown. Shared-scope destroys require `ALLOW_SHARED_SCOPE_DESTROY=true`.
