resource "aws_dynamodb_table" "test-dynamodb-table" {
  name           = "${var.short_prefix}-test-dynamodb-table"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "message"
    type = "S"  
  }

global_secondary_index {
    name            = "message-index"
    hash_key        = "message"
    projection_type = "ALL"
  }

}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.test-dynamodb-table.name
}
