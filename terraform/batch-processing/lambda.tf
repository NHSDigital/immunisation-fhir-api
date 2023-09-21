locals {
  lambda_file_name = "batch_processing.py"
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/src/${local.lambda_file_name}"
  output_path = "build/batch_processing_lambda.zip"
}

resource "aws_lambda_function" "batch_processing_lambda" {
    role             = aws_iam_role.batch_processing_lambda_role.arn
    timeout          = 300
    filename         = data.archive_file.lambda_zip.output_path
    function_name    = "${var.short_prefix}_batch_processing_lambda"
    handler          = "batch_processing.lambda_handler"
    runtime          = "python3.9"
    source_code_hash = data.archive_file.lambda_zip.output_base64sha256
}
