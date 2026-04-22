#!/usr/bin/env bash

set -euo pipefail

mode="${1:-prepare-state}"
sub_environment="${SUB_ENVIRONMENT:-${sub_environment:-}}"

if [[ -z "${sub_environment}" ]]; then
  echo "SUB_ENVIRONMENT must be set."
  exit 1
fi

if [[ ! "${sub_environment}" =~ -(blue|green)$ ]]; then
  echo "Skipping Lambda trigger handoff for ${sub_environment}."
  exit 0
fi

current_colour="${BASH_REMATCH[1]}"
counterpart_colour="blue"
if [[ "${current_colour}" == "blue" ]]; then
  counterpart_colour="green"
fi

counterpart_sub_environment="${sub_environment%-${current_colour}}-${counterpart_colour}"
current_workspace="$(terraform workspace show)"

if [[ "${current_workspace}" != "${sub_environment}" ]]; then
  echo "Terraform workspace ${current_workspace} does not match SUB_ENVIRONMENT ${sub_environment}."
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

resolve_event_source_arns() {
  id_sync_queue_arn="$(terraform output -raw id_sync_queue_arn)"
  events_table_name="$(terraform output -raw dynamodb_table_name)"
  delta_event_source_arn="$(aws dynamodb describe-table \
    --table-name "${events_table_name}" \
    --query 'Table.LatestStreamArn' \
    --output text)"

  if [[ -z "${delta_event_source_arn}" || "${delta_event_source_arn}" == "None" ]]; then
    echo "Unable to resolve the DynamoDB stream ARN for ${events_table_name}."
    exit 1
  fi
}

prepare_state() {
  local address="$1"
  local event_source_arn="$2"
  local counterpart_function_name="$3"
  local target_function_name="$4"
  local mapping_uuid=""

  mapping_uuid="$(lookup_mapping_uuid "${event_source_arn}" "${counterpart_function_name}")"
  if [[ -z "${mapping_uuid}" ]]; then
    mapping_uuid="$(lookup_mapping_uuid "${event_source_arn}" "${target_function_name}")"
  fi

  if [[ -z "${mapping_uuid}" ]]; then
    echo "Unable to find an event source mapping for ${address}."
    exit 1
  fi

  terraform state rm "${address}" >/dev/null 2>&1 || true
  terraform import "${address}" "${mapping_uuid}" >/dev/null

  echo "Imported ${address} into workspace ${sub_environment} using ${mapping_uuid}."
}

cleanup_stale_mapping() {
  local event_source_arn="$1"
  local counterpart_function_name="$2"
  local target_function_name="$3"
  local counterpart_uuid=""
  local target_uuid=""

  counterpart_uuid="$(lookup_mapping_uuid "${event_source_arn}" "${counterpart_function_name}")"
  target_uuid="$(lookup_mapping_uuid "${event_source_arn}" "${target_function_name}")"

  if [[ -z "${target_uuid}" || "${target_uuid}" == "${counterpart_uuid}" ]]; then
    return 0
  fi

  aws lambda delete-event-source-mapping --uuid "${target_uuid}" >/dev/null
  echo "Deleted stale event source mapping ${target_uuid} for ${target_function_name}."
}

resolve_event_source_arns

target_delta_function="imms-${sub_environment}-delta-lambda"
counterpart_delta_function="imms-${counterpart_sub_environment}-delta-lambda"
target_id_sync_function="imms-${sub_environment}-id-sync-lambda"
counterpart_id_sync_function="imms-${counterpart_sub_environment}-id-sync-lambda"

case "${mode}" in
  prepare-state)
    prepare_state \
      "aws_lambda_event_source_mapping.delta_trigger" \
      "${delta_event_source_arn}" \
      "${counterpart_delta_function}" \
      "${target_delta_function}"
    prepare_state \
      "aws_lambda_event_source_mapping.id_sync_sqs_trigger" \
      "${id_sync_queue_arn}" \
      "${counterpart_id_sync_function}" \
      "${target_id_sync_function}"
    ;;
  cleanup-stale)
    cleanup_stale_mapping \
      "${delta_event_source_arn}" \
      "${counterpart_delta_function}" \
      "${target_delta_function}"
    cleanup_stale_mapping \
      "${id_sync_queue_arn}" \
      "${counterpart_id_sync_function}" \
      "${target_id_sync_function}"
    ;;
  *)
    echo "Unsupported mode: ${mode}. Use prepare-state or cleanup-stale."
    exit 1
    ;;
esac
