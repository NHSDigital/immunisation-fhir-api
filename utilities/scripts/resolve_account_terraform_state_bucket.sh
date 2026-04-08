#!/bin/bash

set -euo pipefail

read -r configured_bucket <<< "${CONFIGURED_ACCOUNT_TERRAFORM_STATE_BUCKET:-}"
read -r state_bucket_environment <<< "${ACCOUNT_TERRAFORM_STATE_ENVIRONMENT:-}"

[ -n "$configured_bucket" ] && printf '%s\n' "$configured_bucket" && exit 0

[ -n "$state_bucket_environment" ] || {
  echo "ACCOUNT_TERRAFORM_STATE_ENVIRONMENT must be set when ACCOUNT_TERRAFORM_STATE_BUCKET is not configured." >&2
  exit 1
}

printf 'immunisation-%s-terraform-state-files\n' "$state_bucket_environment"
