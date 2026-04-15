output "mns_test_queue_url" {
  value       = var.enable_mns_test_queue ? aws_sqs_queue.mns_test_notification[0].url : null
  description = "URL of the MNS test notifications queue (DEV only)"
}

output "mns_test_queue_arn" {
  value       = var.enable_mns_test_queue ? aws_sqs_queue.mns_test_notification[0].arn : null
  description = "ARN of the MNS test notifications queue (DEV only)"
}
