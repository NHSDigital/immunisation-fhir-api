output "service_domain_name" {
  value = local.service_domain_name
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.events-dynamodb-table.name
}

output "imms_delta_table_name" {
  value = aws_dynamodb_table.delta-dynamodb-table.name
}

output "aws_sqs_queue_name" {
  value = aws_sqs_queue.dlq.name
}

output "id_sync_queue_arn" {
  description = "The ARN of the ID Sync (MNS NHS Number change) SQS queue"
  value       = aws_sqs_queue.id_sync_queue.arn
}

output "mns_test_queue_url" {
  value       = module.mns_publisher.mns_test_queue_url
  description = "URL of the MNS test notifications queue (from mns_publisher module) - DEV only"
}

output "mns_test_queue_arn" {
  value       = module.mns_publisher.mns_test_queue_arn
  description = "ARN of the MNS test notifications queue (from mns_publisher module) - DEV only"
}
