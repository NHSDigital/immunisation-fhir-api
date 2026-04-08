#!/bin/bash

set -o nounset errexit pipefail

trim() {
  local value="${1-}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

configured_bucket="$(trim "${CONFIGURED_ACCOUNT_TERRAFORM_STATE_BUCKET:-}")"
state_bucket_environment="$(trim "${ACCOUNT_TERRAFORM_STATE_ENVIRONMENT:-}")"

if [ -n "$configured_bucket" ]; then
  printf '%s\n' "$configured_bucket"
  exit 0
fi

if [ -z "$state_bucket_environment" ]; then
  echo "ACCOUNT_TERRAFORM_STATE_ENVIRONMENT must be set when ACCOUNT_TERRAFORM_STATE_BUCKET is not configured." >&2
  exit 1
fi

printf 'immunisation-%s-terraform-state-files\n' "$state_bucket_environment"
