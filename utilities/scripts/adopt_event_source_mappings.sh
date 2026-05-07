#!/usr/bin/env bash

set -euo pipefail

environment="${ENVIRONMENT:-${environment:-}}"
sub_environment="${SUB_ENVIRONMENT:-${sub_environment:-}}"
resource_scope="${RESOURCE_SCOPE:-${resource_scope:-}}"
action="${EVENT_SOURCE_MAPPING_ACTION:-adopt}"

require_value() {
  local name="$1"
  local value="$2"

  if [[ -z "${value}" ]]; then
    echo "${name} must be set."
    exit 1
  fi
}

require_value "ENVIRONMENT" "${environment}"
require_value "SUB_ENVIRONMENT" "${sub_environment}"
require_value "RESOURCE_SCOPE" "${resource_scope}"

require_controlled_adoption() {
  if [[ "${ALLOW_EVENT_SOURCE_MAPPING_ADOPTION:-}" != "true" ]]; then
    echo "ALLOW_EVENT_SOURCE_MAPPING_ADOPTION=true must be set for the controlled event source mapping migration."
    exit 1
  fi
}

log_mappings() {
  local mappings_json="$1"
  local event_source_arn="$2"
  local function_name="$3"

  if jq -e '.EventSourceMappings | length == 0' <<<"${mappings_json}" >/dev/null; then
    echo "No event source mappings found for ${function_name} on ${event_source_arn}." >&2
    return 0
  fi

  echo "Event source mappings found for ${function_name} on ${event_source_arn}:" >&2
  jq -r \
    '.EventSourceMappings[]
      | "  UUID=\(.UUID) State=\(.State) FunctionArn=\(.FunctionArn // "unknown")"' \
    <<<"${mappings_json}" >&2
}

lookup_mapping_uuid() {
  local event_source_arn="$1"
  local function_name="$2"
  local mappings_json
  local active_mapping_count
  local mapping_uuid

  mappings_json="$(aws lambda list-event-source-mappings \
    --event-source-arn "${event_source_arn}" \
    --function-name "${function_name}" \
    --output json)"

  log_mappings "${mappings_json}" "${event_source_arn}" "${function_name}"

  active_mapping_count="$(jq '[.EventSourceMappings[]? | select(.State != "Deleting")] | length' <<<"${mappings_json}")"

  if ((active_mapping_count > 1)); then
    echo "Ambiguous event source mappings for ${function_name} on ${event_source_arn}; refusing to continue." >&2
    exit 1
  fi

  if ((active_mapping_count == 0)); then
    return 0
  fi

  mapping_uuid="$(jq -r '.EventSourceMappings[] | select(.State != "Deleting") | .UUID' <<<"${mappings_json}")"
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

resolve_mapping_uuid() {
  local address="$1"
  local event_source_arn="$2"
  local target_function_name="$3"
  local counterpart_function_name="${4:-}"
  local target_mapping_uuid=""
  local counterpart_mapping_uuid=""
  local mapping_uuid=""
  local resource_in_state="false"

  if state_has_resource "${address}"; then
    resource_in_state="true"
  fi

  target_mapping_uuid="$(lookup_mapping_uuid "${event_source_arn}" "${target_function_name}")"

  if [[ -n "${counterpart_function_name}" ]]; then
    counterpart_mapping_uuid="$(lookup_mapping_uuid "${event_source_arn}" "${counterpart_function_name}")"
  fi

  if [[ -n "${target_mapping_uuid}" && -n "${counterpart_mapping_uuid}" ]]; then
    echo "Both target and counterpart mappings exist for ${address}; refusing to continue." >&2
    echo "Target UUID: ${target_mapping_uuid}" >&2
    echo "Counterpart UUID: ${counterpart_mapping_uuid}" >&2
    exit 1
  fi

  if [[ "${resource_in_state}" == "true" ]]; then
    echo "${address} is already managed in this workspace." >&2
    return 0
  fi

  if [[ -n "${counterpart_mapping_uuid}" ]]; then
    mapping_uuid="${counterpart_mapping_uuid}"
  else
    mapping_uuid="${target_mapping_uuid}"
  fi

  if [[ -z "${mapping_uuid}" ]]; then
    echo "No existing event source mapping found for ${address}; Terraform will create it." >&2
    return 0
  fi

  printf '%s' "${mapping_uuid}"
}

import_mapping() {
  local address="$1"
  local mapping_uuid="$2"

  shift 2

  if [[ -z "${mapping_uuid}" ]]; then
    return 0
  fi

  terraform import -input=false "$@" "${address}" "${mapping_uuid}" >/dev/null
  echo "Imported ${address} into workspace ${resource_scope} using ${mapping_uuid}."
}

verify_mapping() {
  local address="$1"
  local event_source_arn="$2"
  local target_function_name="$3"
  local counterpart_function_name="${4:-}"
  local target_mapping_uuid=""
  local counterpart_mapping_uuid=""

  target_mapping_uuid="$(lookup_mapping_uuid "${event_source_arn}" "${target_function_name}")"

  if [[ -z "${target_mapping_uuid}" ]]; then
    echo "No final event source mapping found for ${address} targeting ${target_function_name}."
    exit 1
  fi

  if [[ -n "${counterpart_function_name}" ]]; then
    counterpart_mapping_uuid="$(lookup_mapping_uuid "${event_source_arn}" "${counterpart_function_name}")"

    if [[ -n "${counterpart_mapping_uuid}" ]]; then
      echo "A stale counterpart mapping remains for ${address}: ${counterpart_mapping_uuid} targets ${counterpart_function_name}."
      exit 1
    fi
  fi

  echo "Verified ${address} targets ${target_function_name} with UUID ${target_mapping_uuid}."
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

case "${action}" in
  adopt)
    delta_mapping_uuid=""
    id_sync_mapping_uuid=""

    require_controlled_adoption

    delta_mapping_uuid="$(resolve_mapping_uuid \
      "aws_lambda_event_source_mapping.delta_trigger" \
      "${delta_event_source_arn}" \
      "${target_delta_function}" \
      "${counterpart_delta_function}")"

    id_sync_mapping_uuid="$(resolve_mapping_uuid \
      "aws_lambda_event_source_mapping.id_sync_sqs_trigger" \
      "${id_sync_queue_arn}" \
      "${target_id_sync_function}" \
      "${counterpart_id_sync_function}")"

    import_mapping \
      "aws_lambda_event_source_mapping.delta_trigger" \
      "${delta_mapping_uuid}" \
      "$@"

    import_mapping \
      "aws_lambda_event_source_mapping.id_sync_sqs_trigger" \
      "${id_sync_mapping_uuid}" \
      "$@"
    ;;
  verify)
    verify_mapping \
      "aws_lambda_event_source_mapping.delta_trigger" \
      "${delta_event_source_arn}" \
      "${target_delta_function}" \
      "${counterpart_delta_function}"

    verify_mapping \
      "aws_lambda_event_source_mapping.id_sync_sqs_trigger" \
      "${id_sync_queue_arn}" \
      "${target_id_sync_function}" \
      "${counterpart_id_sync_function}"
    ;;
  *)
    echo "Unsupported EVENT_SOURCE_MAPPING_ACTION: ${action}"
    exit 1
    ;;
esac
