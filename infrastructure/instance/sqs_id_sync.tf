resource "aws_sqs_queue" "id_sync_queue" {
  name                       = "imms-${local.resource_scope}-id-sync-queue"
  kms_master_key_id          = data.aws_kms_key.existing_id_sync_sqs_encryption_key.arn
  visibility_timeout_seconds = 360
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.id_sync_dlq.arn
    maxReceiveCount     = 4
  })
}

resource "aws_sqs_queue" "id_sync_dlq" {
  name = "imms-${local.resource_scope}-id-sync-dlq"
}

resource "aws_sqs_queue_redrive_allow_policy" "id_sync_queue_redrive_allow_policy" {
  queue_url = aws_sqs_queue.id_sync_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.id_sync_queue.arn]
  })
}

data "aws_iam_policy_document" "id_sync_sqs_policy" {
  statement {
    sid    = "mns-allow-send"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${var.mns_account_id}:role/nhs-mns-events-lambda-delivery"]
    }

    actions = [
      "sqs:SendMessage",
    ]

    resources = [
      aws_sqs_queue.id_sync_queue.arn
    ]
  }

  statement {
    sid    = "id-sync-allow-receive"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.id_sync_lambda_exec_role.arn]
    }

    actions = [
      "sqs:ReceiveMessage",
    ]

    resources = [
      aws_sqs_queue.id_sync_queue.arn
    ]
  }
}

resource "aws_sqs_queue_policy" "id_sync_sqs_policy" {
  queue_url = aws_sqs_queue.id_sync_queue.id
  policy    = data.aws_iam_policy_document.id_sync_sqs_policy.json
}
