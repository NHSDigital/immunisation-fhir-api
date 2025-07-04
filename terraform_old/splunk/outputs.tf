output "firehose_stream_name" {
    value = aws_kinesis_firehose_delivery_stream.splunk_firehose_stream.name
}