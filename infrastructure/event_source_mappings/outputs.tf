output "id_sync_queue_arn" {
  description = "The ARN of the ID Sync (MNS NHS Number change) SQS queue"
  value       = data.aws_sqs_queue.id_sync.arn
}

output "delta_trigger_uuid" {
  description = "The UUID of the Delta Lambda event source mapping"
  value       = aws_lambda_event_source_mapping.delta_trigger.id
}

output "delta_trigger_function_arn" {
  description = "The ARN of the Delta Lambda targeted by the event source mapping"
  value       = data.aws_lambda_function.delta.arn
}

output "delta_trigger_state" {
  description = "The current state of the Delta Lambda event source mapping"
  value       = aws_lambda_event_source_mapping.delta_trigger.state
}

output "id_sync_sqs_trigger_uuid" {
  description = "The UUID of the ID Sync SQS event source mapping"
  value       = aws_lambda_event_source_mapping.id_sync_sqs_trigger.id
}

output "id_sync_sqs_trigger_function_arn" {
  description = "The ARN of the ID Sync Lambda targeted by the event source mapping"
  value       = data.aws_lambda_function.id_sync.arn
}

output "id_sync_sqs_trigger_state" {
  description = "The current state of the ID Sync SQS event source mapping"
  value       = aws_lambda_event_source_mapping.id_sync_sqs_trigger.state
}
