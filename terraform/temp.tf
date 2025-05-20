# TODO - conditional import blocks aren't possible in Terraform
# Might need to do this via the CLI instead
# import {
#     id = "immunisation-batch-internal-dev-audit-table"
#     to = aws_dynamodb_table.audit-table
# }
# import {
#     id = "immunisation-batch-int-audit-table"
#     to = aws_dynamodb_table.audit-table
# }
# import {
#     id = "immunisation-batch-ref-audit-table"
#     to = aws_dynamodb_table.audit-table
# }
# import {
#     id = "immunisation-batch-prod-audit-table"
#     to = aws_dynamodb_table.audit-table
# }

# import {
#     id = "imms-internal-dev-delta"
#     to = aws_dynamodb_table.delta-dynamodb-table
# }
# import {
#     id = "imms-int-delta"
#     to = aws_dynamodb_table.delta-dynamodb-table
# }
# import {
#     id = "imms-ref-delta"
#     to = aws_dynamodb_table.delta-dynamodb-table
# }
# import {
#     id = "imms-prod-delta"
#     to = aws_dynamodb_table.delta-dynamodb-table
# }

# import {
#     id = "imms-internal-dev-imms-events"
#     to = aws_dynamodb_table.events-dynamodb-table
# }
# import {
#     id = "imms-int-imms-events"
#     to = aws_dynamodb_table.events-dynamodb-table
# }
# import {
#     id = "imms-ref-imms-events"
#     to = aws_dynamodb_table.events-dynamodb-table
# }
# import {
#     id = "imms-prod-imms-events"
#     to = aws_dynamodb_table.events-dynamodb-table
# }
