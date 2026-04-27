output "id_sync_queue_arn" {
  description = "The ARN of the ID Sync (MNS NHS Number change) SQS queue"
  value       = data.aws_sqs_queue.id_sync.arn
}
