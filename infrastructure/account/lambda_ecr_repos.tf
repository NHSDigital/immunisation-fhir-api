locals {
  lambda_source_arn_prefix = "arn:aws:lambda:${var.aws_region}:${var.imms_account_id}:function:imms-"

  lambda_ecr_repositories = {
    operation = {
      name = "imms-backend-repo"
      lambda_source_names = [
        "*_get_status",
        "*_not_found",
        "*_search_imms",
        "*_get_imms",
        "*_delete_imms",
        "*_create_imms",
        "*_update_imms"
      ]
    }
    batch_processor_filter = {
      name                = "imms-batch-processor-filter-repo"
      lambda_source_names = ["*-batch-processor-filter-lambda"]
    }
    delta = {
      name                = "imms-delta-backend-repo"
      lambda_source_names = ["*-delta-lambda"]
    }
    filenameprocessor = {
      name                = "imms-filenameprocessor-repo"
      lambda_source_names = ["*-filenameproc-lambda"]
    }
    id_sync = {
      name                = "imms-id-sync-repo"
      lambda_source_names = ["*-id-sync-lambda"]
    }
    mesh_processor = {
      name                = "imms-mesh-processor-repo"
      lambda_source_names = ["*-mesh-processor-lambda"]
    }
    mns_publisher = {
      name                = "imms-mns-publisher-repo"
      lambda_source_names = ["*-mns-publisher-lambda"]
    }
    ack_backend = {
      name                = "imms-ackbackend-repo"
      lambda_source_names = ["*-ack-lambda"]
    }
    recordforwarder = {
      name                = "imms-recordforwarder-repo"
      lambda_source_names = ["*-forwarding-lambda"]
    }
    recordprocessor = {
      name = "imms-recordprocessor-repo"
      lifecycle_policy = jsonencode({
        rules = [
          {
            rulePriority = 1
            description  = "Keep last 10 images."
            selection = {
              tagStatus   = "any"
              countType   = "imageCountMoreThan"
              countNumber = 10
            }
            action = {
              type = "expire"
            }
          }
        ]
      })
    }
    redis_sync = {
      name                = "imms-redis-sync-repo"
      lambda_source_names = ["*-redis-sync-lambda"]
    }
  }
}
#lambda repo
resource "aws_ecr_repository" "lambda_repository" {
  for_each = local.lambda_ecr_repositories

  image_scanning_configuration {
    scan_on_push = true
  }

  image_tag_mutability = "IMMUTABLE"
  name                 = each.value.name
}

resource "aws_ecr_repository_policy" "lambda_repository_image_retrieval_policy" {
  for_each = {
    for key, repo in local.lambda_ecr_repositories : key => repo if try(repo.lambda_source_names, null) != null
  }

  repository = aws_ecr_repository.lambda_repository[each.key].name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "LambdaECRImageRetrievalPolicy"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Condition = {
          StringLike = {
            "aws:sourceArn" = formatlist("${local.lambda_source_arn_prefix}%s", each.value.lambda_source_names)
          }
        }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "lambda_repository_lifecycle_policy" {
  for_each = {
    for key, repo in local.lambda_ecr_repositories : key => repo if try(repo.lifecycle_policy, null) != null
  }

  repository = aws_ecr_repository.lambda_repository[each.key].name
  policy     = each.value.lifecycle_policy
}

moved {
  from = aws_ecr_repository.ackbackend_repository
  to   = aws_ecr_repository.lambda_repository["ack_backend"]
}

moved {
  from = aws_ecr_repository_policy.ackbackend_repository_lambda_image_retrieval_policy
  to   = aws_ecr_repository_policy.lambda_repository_image_retrieval_policy["ack_backend"]
}

moved {
  from = aws_ecr_repository.recordprocessor_repository
  to   = aws_ecr_repository.lambda_repository["recordprocessor"]
}

moved {
  from = aws_ecr_lifecycle_policy.recordprocessor_repository_lifecycle_policy
  to   = aws_ecr_lifecycle_policy.lambda_repository_lifecycle_policy["recordprocessor"]
}

moved {
  from = aws_ecr_repository.operation_lambda_repository
  to   = aws_ecr_repository.lambda_repository["operation"]
}

moved {
  from = aws_ecr_repository_policy.operation_lambda_ECRImageRetreival_policy
  to   = aws_ecr_repository_policy.lambda_repository_image_retrieval_policy["operation"]
}

moved {
  from = aws_ecr_repository.batch_processor_filter_lambda_repository
  to   = aws_ecr_repository.lambda_repository["batch_processor_filter"]
}

moved {
  from = aws_ecr_repository_policy.batch_processor_filter_lambda_ECRImageRetreival_policy
  to   = aws_ecr_repository_policy.lambda_repository_image_retrieval_policy["batch_processor_filter"]
}

moved {
  from = aws_ecr_repository.delta_lambda_repository
  to   = aws_ecr_repository.lambda_repository["delta"]
}

moved {
  from = aws_ecr_repository_policy.delta_lambda_ECRImageRetreival_policy
  to   = aws_ecr_repository_policy.lambda_repository_image_retrieval_policy["delta"]
}

moved {
  from = aws_ecr_repository.file_name_processor_lambda_repository
  to   = aws_ecr_repository.lambda_repository["filenameprocessor"]
}

moved {
  from = aws_ecr_repository_policy.filenameprocessor_lambda_ECRImageRetreival_policy
  to   = aws_ecr_repository_policy.lambda_repository_image_retrieval_policy["filenameprocessor"]
}

moved {
  from = aws_ecr_repository.id_sync_lambda_repository
  to   = aws_ecr_repository.lambda_repository["id_sync"]
}

moved {
  from = aws_ecr_repository_policy.id_sync_lambda_ECRImageRetreival_policy
  to   = aws_ecr_repository_policy.lambda_repository_image_retrieval_policy["id_sync"]
}

moved {
  from = aws_ecr_repository.forwarder_lambda_repository
  to   = aws_ecr_repository.lambda_repository["recordforwarder"]
}

moved {
  from = aws_ecr_repository_policy.forwarder_lambda_ECRImageRetreival_policy
  to   = aws_ecr_repository_policy.lambda_repository_image_retrieval_policy["recordforwarder"]
}

moved {
  from = aws_ecr_repository.redis_sync_lambda_repository
  to   = aws_ecr_repository.lambda_repository["redis_sync"]
}

moved {
  from = aws_ecr_repository_policy.redis_sync_lambda_ECRImageRetreival_policy
  to   = aws_ecr_repository_policy.lambda_repository_image_retrieval_policy["redis_sync"]
}

moved {
  from = module.mns_publisher.aws_ecr_repository.mns_publisher_lambda_repository
  to   = aws_ecr_repository.lambda_repository["mns_publisher"]
}

moved {
  from = module.mns_publisher.aws_ecr_repository_policy.mns_publisher_lambda_ecr_image_retrieval_policy
  to   = aws_ecr_repository_policy.lambda_repository_image_retrieval_policy["mns_publisher"]
}
