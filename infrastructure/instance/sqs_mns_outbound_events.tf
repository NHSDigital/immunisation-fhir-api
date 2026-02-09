resource "aws_sqs_queue" "mns_outbound_events" {
  name                       = "${local.resource_scope}-mns-outbound-events"
  fifo_queue                 = false
  visibility_timeout_seconds = 120
}
