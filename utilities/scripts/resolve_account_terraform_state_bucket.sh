#!/bin/bash

set -o nounset errexit pipefail

configured_bucket="$(printf '%s' "${CONFIGURED_ACCOUNT_TERRAFORM_STATE_BUCKET:-}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
state_bucket_environment="$(printf '%s' "${ACCOUNT_TERRAFORM_STATE_ENVIRONMENT:-}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
terraform_workspace="$(printf '%s' "${ACCOUNT_TERRAFORM_WORKSPACE:-}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

if [ -n "$configured_bucket" ]; then
  printf '%s\n' "$configured_bucket"
  exit 0
fi

if [ -z "$terraform_workspace" ]; then
  echo "ACCOUNT_TERRAFORM_WORKSPACE must be set." >&2
  exit 1
fi

state_key="env:/${terraform_workspace}/state"

bucket_contains_state() {
  local bucket_name="$1"
  aws s3api head-object --bucket "$bucket_name" --key "$state_key" >/dev/null 2>&1
}

candidate_buckets=()

if [ -n "$state_bucket_environment" ]; then
  candidate_buckets+=("immunisation-${state_bucket_environment}-terraform-state-files")
fi

candidate_buckets+=("immunisation-terraform-state-files")

for candidate_bucket in "${candidate_buckets[@]}"; do
  if bucket_contains_state "$candidate_bucket"; then
    printf '%s\n' "$candidate_bucket"
    exit 0
  fi
done

mapfile -t buckets < <(
  aws s3api list-buckets --query 'Buckets[].Name' --output text |
  tr '\t' '\n' |
  grep -E '^immunisation(-[a-z0-9-]+)?-terraform-state(-files)?$'
)

matching_buckets=()

for bucket in "${buckets[@]}"; do
  if bucket_contains_state "$bucket"; then
    matching_buckets+=("$bucket")
  fi
done

if [ "${#matching_buckets[@]}" -ne 1 ]; then
  echo "Expected exactly 1 terraform state bucket containing ${state_key}, found ${#matching_buckets[@]}." >&2
  echo "Set repo/environment variable ACCOUNT_TERRAFORM_STATE_BUCKET to remove ambiguity." >&2
  if [ "${#matching_buckets[@]}" -gt 0 ]; then
    printf '%s\n' "${matching_buckets[@]}" >&2
  else
    echo "Checked buckets:" >&2
    printf '%s\n' "${buckets[@]}" >&2
  fi
  exit 1
fi

printf '%s\n' "${matching_buckets[0]}"
