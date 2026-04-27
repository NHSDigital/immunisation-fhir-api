#!/usr/bin/env bash

set -euo pipefail

environment="${ENVIRONMENT:-${environment:-}}"
sub_environment="${SUB_ENVIRONMENT:-${sub_environment:-}}"
resource_scope="${RESOURCE_SCOPE:-${resource_scope:-}}"

if [[ -z "${environment}" ]]; then
  echo "ENVIRONMENT must be set."
  exit 1
fi

if [[ -z "${sub_environment}" ]]; then
  echo "SUB_ENVIRONMENT must be set."
  exit 1
fi

if [[ -z "${resource_scope}" ]]; then
  echo "RESOURCE_SCOPE must be set."
  exit 1
fi

lookup_mapping_uuid() {
  local event_source_arn="$1"
  local function_name="$2"
  local mapping_uuid

  mapping_uuid="$(aws lambda list-event-source-mappings \
    --event-source-arn "${event_source_arn}" \
    --function-name "${function_name}" \
    --query 'EventSourceMappings[0].UUID' \
    --output text)"

  if [[ "${mapping_uuid}" == "None" ]]; then
    return 0
  fi

  printf '%s' "${mapping_uuid}"
}

counterpart_for_sub_environment() {
  local name="$1"

  case "${name}" in
    blue)
      printf 'green'
      ;;
    green)
      printf 'blue'
      ;;
    *-blue)
      printf '%s-green' "${name%-blue}"
      ;;
    *-green)
      printf '%s-blue' "${name%-green}"
      ;;
    *)
      return 1
      ;;
  esac
}

state_has_resource() {
  local address="$1"

  terraform state show "${address}" >/dev/null 2>&1
}

adopt_mapping() {
  local address="$1"
  local event_source_arn="$2"
  local target_function_name="$3"
  local counterpart_function_name="${4:-}"
  local mapping_uuid=""

  shift 4

  if state_has_resource "${address}"; then
    echo "${address} is already managed in this workspace."
    return 0
  fi

  mapping_uuid="$(lookup_mapping_uuid "${event_source_arn}" "${target_function_name}")"
  if [[ -z "${mapping_uuid}" && -n "${counterpart_function_name}" ]]; then
    mapping_uuid="$(lookup_mapping_uuid "${event_source_arn}" "${counterpart_function_name}")"
  fi

  if [[ -z "${mapping_uuid}" ]]; then
    echo "No existing event source mapping found for ${address}; Terraform will create it."
    return 0
  fi

  terraform import -input=false "$@" "${address}" "${mapping_uuid}" >/dev/null
  echo "Imported ${address} into workspace ${resource_scope} using ${mapping_uuid}."
}

events_table_name="imms-${resource_scope}-imms-events"
delta_event_source_arn="$(aws dynamodb describe-table \
  --table-name "${events_table_name}" \
  --query 'Table.LatestStreamArn' \
  --output text)"

if [[ -z "${delta_event_source_arn}" || "${delta_event_source_arn}" == "None" ]]; then
  echo "Unable to resolve the DynamoDB stream ARN for ${events_table_name}."
  exit 1
fi

id_sync_queue_name="imms-${resource_scope}-id-sync-queue"
id_sync_queue_url="$(aws sqs get-queue-url \
  --queue-name "${id_sync_queue_name}" \
  --query 'QueueUrl' \
  --output text)"
id_sync_queue_arn="$(aws sqs get-queue-attributes \
  --queue-url "${id_sync_queue_url}" \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' \
  --output text)"

target_delta_function="imms-${sub_environment}-delta-lambda"
target_id_sync_function="imms-${sub_environment}-id-sync-lambda"
counterpart_delta_function=""
counterpart_id_sync_function=""

if [[ "${resource_scope}" != "${sub_environment}" ]] && counterpart_sub_environment="$(counterpart_for_sub_environment "${sub_environment}")"; then
  counterpart_delta_function="imms-${counterpart_sub_environment}-delta-lambda"
  counterpart_id_sync_function="imms-${counterpart_sub_environment}-id-sync-lambda"
fi

adopt_mapping \
  "aws_lambda_event_source_mapping.delta_trigger" \
  "${delta_event_source_arn}" \
  "${target_delta_function}" \
  "${counterpart_delta_function}" \
  "$@"

adopt_mapping \
  "aws_lambda_event_source_mapping.id_sync_sqs_trigger" \
  "${id_sync_queue_arn}" \
  "${target_id_sync_function}" \
  "${counterpart_id_sync_function}" \
  "$@"
