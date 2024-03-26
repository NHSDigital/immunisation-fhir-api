output "service_domain_name" {
  value = local.service_domain_name
}

output "imms_delta_table_name" {
  value = aws_dynamodb_table.delta-dynamodb-table.name
}
