#!/bin/bash

set -o nounset errexit pipefail

if [ -n "${CONFIGURED_ACCOUNT_TERRAFORM_STATE_BUCKET:-}" ]; then
  printf '%s\n' "$CONFIGURED_ACCOUNT_TERRAFORM_STATE_BUCKET"
  exit 0
fi

mapfile -t buckets < <(
  aws s3api list-buckets --query 'Buckets[].Name' --output text |
  tr '\t' '\n' |
  grep -E '^immunisation-dev-terraform-state(-files)?$'
)

if [ "${#buckets[@]}" -ne 1 ]; then
  echo "Expected exactly 1 dev account terraform state bucket, found ${#buckets[@]}." >&2
  echo "Set repo/environment variable ACCOUNT_TERRAFORM_STATE_BUCKET to remove ambiguity." >&2
  printf '%s\n' "${buckets[@]}" >&2
  exit 1
fi

printf '%s\n' "${buckets[0]}"
