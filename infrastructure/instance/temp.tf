# TODO - conditional import blocks aren't possible in Terraform
# We'll need to perform equivalent actions using the CLI instead

# import {
#   id = "immunisation-batch-internal-dev-audit-table"
#   to = aws_dynamodb_table.audit-table
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
#   id = "imms-internal-dev-delta"
#   to = aws_dynamodb_table.delta-dynamodb-table
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
#   id = "imms-internal-dev-imms-events"
#   to = aws_dynamodb_table.events-dynamodb-table
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

# import {
#   id = "immunisation-batch-internal-dev-data-destinations"
#   to = aws_s3_bucket.batch_data_destination_bucket
# }
# import {
#     id = "immunisation-batch-int-data-destinations"
#     to = aws_s3_bucket.batch_data_destination_bucket
# }
# import {
#     id = "immunisation-batch-ref-data-destinations"
#     to = aws_s3_bucket.batch_data_destination_bucket
# }
# import {
#     id = "immunisation-batch-prod-data-destinations"
#     to = aws_s3_bucket.batch_data_destination_bucket
# }

# import {
#   id = "immunisation-batch-internal-dev-data-destinations"
#   to = aws_s3_bucket_policy.batch_data_destination_bucket_policy
# }
# import {
#   id = "immunisation-batch-int-data-destinations"
#   to = aws_s3_bucket_policy.batch_data_destination_bucket_policy
# }
# import {
#   id = "immunisation-batch-ref-data-destinations"
#   to = aws_s3_bucket_policy.batch_data_destination_bucket_policy
# }
# import {
#   id = "immunisation-batch-prod-data-destinations"
#   to = aws_s3_bucket_policy.batch_data_destination_bucket_policy
# }

# import {
#   id = "immunisation-batch-internal-dev-data-destinations"
#   to = aws_s3_bucket_server_side_encryption_configuration.s3_batch_destination_encryption
# }
# import {
#   id = "immunisation-batch-int-data-destinations"
#   to = aws_s3_bucket_server_side_encryption_configuration.s3_batch_destination_encryption
# }
# import {
#   id = "immunisation-batch-ref-data-destinations"
#   to = aws_s3_bucket_server_side_encryption_configuration.s3_batch_destination_encryption
# }
# import {
#   id = "immunisation-batch-prod-data-destinations"
#   to = aws_s3_bucket_server_side_encryption_configuration.s3_batch_destination_encryption
# }

# import {
#   id = "immunisation-batch-prod-data-destinations"
#   to = aws_s3_bucket_lifecycle_configuration.data_destinations
# }

# import {
#   id = "imms-internal-dev-supplier-config"
#   to = aws_s3_bucket.batch_config_bucket[0]
# }
# import {
#   id = "imms-prod-supplier-config"
#   to = aws_s3_bucket.batch_config_bucket[0]
# }

# import {
#   id = "imms-internal-dev-supplier-config"
#   to = aws_s3_bucket_public_access_block.batch_config_bucket_public_access_block[0]
# }
# import {
#   id = "imms-prod-supplier-config"
#   to = aws_s3_bucket_public_access_block.batch_config_bucket_public_access_block[0]
# }

# import {
#   id = "imms-internal-dev-supplier-config"
#   to = aws_s3_bucket_policy.batch_config_bucket_policy[0]
# }
# import {
#   id = "imms-prod-supplier-config"
#   to = aws_s3_bucket_policy.batch_config_bucket_policy[0]
# }

# TODO - delete after ack backend ECR ownership migration has been applied in all environments

removed {
  from = aws_ecr_repository.ack_lambda_repository

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_ecr_repository_policy.ack_lambda_ECRImageRetreival_policy

  lifecycle {
    destroy = false
  }
}

removed {
  from = module.ack_processor_docker_image

  lifecycle {
    destroy = false
  }
}
