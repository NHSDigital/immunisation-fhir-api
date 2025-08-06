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

output "aws_sns_topic_name" {
  value = aws_sns_topic.delta_sns.name
}

output "id_sync_queue_arn" {
  description = "The ARN of the created SQS queue"
  value       = aws_sqs_queue.id_sync_queue.arn
}

output "lambdas_dir_abs_path" {
  value = local.id_sync_lambda_dir
}

output "lambdas_dir_normal" {
  value = "${local.id_sync_lambda_dir}/id_sync"
}
