#!/bin/bash
set -e
table_name="imms-internal-dev-delta"
concurrency=10  # Max concurrent deletions

total_records=$(aws dynamodb describe-table --table-name "$table_name" --query "Table.ItemCount" --output text)
echo "Total records in table '$table_name': $total_records"

last_evaluated_key=""
processed_records=0
page_size=150

# Semaphore to limit concurrency
function wait_for_jobs {
  while (( $(jobs -rp | wc -l) >= concurrency )); do
    sleep 0.2
  done
}

while :; do
  if [ -n "$last_evaluated_key" ]; then
    scan_output=$(aws dynamodb scan --table-name "$table_name" \
      --max-items "$page_size" \
      --starting-token "$last_evaluated_key")
  else
    scan_output=$(aws dynamodb scan --table-name "$table_name" \
      --max-items "$page_size")
  fi

    keys=$(echo "$scan_output" | jq -c '.Items[] | {PK: {"S": .PK.S}}')

  last_evaluated_key=$(echo "$scan_output" | jq -r '.NextToken // empty')

  if [ -z "$keys" ]; then
    break
  fi

  while read -r key; do
    wait_for_jobs

    {
      aws dynamodb delete-item --table-name "$table_name" --key "$key" >/dev/null
      ((processed_records++))
      progress=$(awk "BEGIN {printf \"%.2f\", ($processed_records/$total_records)*100}")
      echo "Deleted: $key. Progress: $processed_records/$total_records ($progress%)"
    } &
  done < <(echo "$keys")

  # Wait for background jobs of this batch to finish before fetching the next page
  wait

  if [ -z "$last_evaluated_key" ]; then
    break
  fi
done

remaining_records=$(aws dynamodb describe-table --table-name "$table_name" --query "Table.ItemCount" --output text)
echo "Remaining records in table '$table_name': $remaining_records"
