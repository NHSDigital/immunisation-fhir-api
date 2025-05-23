# TODO - delete this file once the state has been updated in all environments

# --- TABLES

removed {
  from = aws_dynamodb_table.audit-table
  lifecycle {
    destroy = false
  }
}
removed {
  from = aws_dynamodb_table.audit-table-int
  lifecycle {
    destroy = false
  }
}
removed {
  from = aws_dynamodb_table.audit-table-ref
  lifecycle {
    destroy = false
  }
}

# ---

removed {
  from = aws_dynamodb_table.delta-dynamodb-table
  lifecycle {
    destroy = false
  }
}
removed {
  from = aws_dynamodb_table.delta-dynamodb-int-table
  lifecycle {
    destroy = false
  }
}
removed {
  from = aws_dynamodb_table.delta-dynamodb-ref-table
  lifecycle {
    destroy = false
  }
}

# ---

removed {
  from = aws_dynamodb_table.events-dynamodb-table
  lifecycle {
    destroy = false
  }
}
removed {
  from = aws_dynamodb_table.events-dynamodb-int-table
  lifecycle {
    destroy = false
  }
}
removed {
  from = aws_dynamodb_table.events-dynamodb-ref-table
  lifecycle {
    destroy = false
  }
}

# --- CONFIG BUCKET

removed {
  from = aws_s3_bucket.batch_config_bucket
  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_s3_bucket_public_access_block.batch_config_bucket_public_access_block
  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_s3_bucket_policy.batch_config_bucket_policy
  lifecycle {
    destroy = false
  }
}

# --- BATCH DESTINATION BUCKET

removed {
  from = aws_s3_bucket.batch_data_destination_bucket
  lifecycle {
    destroy = false
  }
}
removed {
  from = aws_s3_bucket.batch_data_destination_int_bucket
  lifecycle {
    destroy = false
  }
}
removed {
  from = aws_s3_bucket.batch_data_destination_ref_bucket
  lifecycle {
    destroy = false
  }
}

# ---

removed {
  from = aws_s3_bucket_policy.batch_data_destination_bucket_policy
  lifecycle {
    destroy = false
  }
}
removed {
  from = aws_s3_bucket_policy.batch_data_destination_int_bucket_policy
  lifecycle {
    destroy = false
  }
}
removed {
  from = aws_s3_bucket_policy.batch_data_destination_ref_bucket_policy
  lifecycle {
    destroy = false
  }
}

# ---

removed {
  from = aws_s3_bucket_server_side_encryption_configuration.s3_batch_destination_encryption
  lifecycle {
    destroy = false
  }
}
removed {
  from = aws_s3_bucket_server_side_encryption_configuration.s3_batch_destination_int_encryption
  lifecycle {
    destroy = false
  }
}
removed {
  from = aws_s3_bucket_server_side_encryption_configuration.s3_batch_destination_ref_encryption
  lifecycle {
    destroy = false
  }
}

# ---

removed {
  from = aws_s3_bucket_lifecycle_configuration.data_destinations
  lifecycle {
    destroy = false
  }
}
