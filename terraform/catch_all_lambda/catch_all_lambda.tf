resource "aws_s3_bucket" "catch_all_lambda_bucket" {
  bucket        = "${var.prefix}-catch-all-lambda-bucket"
  force_destroy = true
}

data "archive_file" "catch_all_lambda_function_code_zip" {
  type        = "zip"
  source_file = "../${path.module}/src/catch_all_lambda.py"
  output_path = "build/${var.catch_all_lambda_zip_name}.zip"
}

#Upload object for the first time, then it gets updated via local-exec
resource "aws_s3_object" "catch_all_lambda_function_code" {
  bucket = aws_s3_bucket.catch_all_lambda_bucket.bucket
  key    = "${var.catch_all_lambda_zip_name}.zip"
  source = "${path.root}/zips/${var.catch_all_lambda_zip_name}.zip"  # Local path to your ZIP file
}

resource "aws_lambda_function" "catch_all_lambda" {
  depends_on  = [null_resource.catch_all_lambda_dist,
                aws_s3_object.catch_all_lambda_function_code
  ]
  s3_bucket=aws_s3_bucket.catch_all_lambda_bucket.bucket
  s3_key  ="${var.catch_all_lambda_zip_name}.zip"
  function_name = "${var.prefix}-catch-all-lambda"
#   source_code_hash = data.aws_s3_object.catch_all_lambda_function_code.etag  # Calculate the hash of the new ZIP file uploaded to s3
  role          = aws_iam_role.catch_all_lambda_role.arn
  handler       = "catch_all_lambda.handler"
  runtime       = "python3.8"
  memory_size   = 1024

  environment {
    variables = {}
  }
}

output "catch_all_lambda_name" {
  value = aws_lambda_function.catch_all_lambda.function_name
}
