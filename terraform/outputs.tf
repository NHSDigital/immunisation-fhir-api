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
