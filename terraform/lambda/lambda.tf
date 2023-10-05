resource "aws_s3_bucket" "lambda_bucket" {
  bucket        = "${var.prefix}-lambda-bucket"
  force_destroy = true
}

#Upload object for the first time, then it gets updated via local-exec
resource "aws_s3_object" "lambda_function_code" {
  bucket = aws_s3_bucket.lambda_bucket.bucket
  key    = "${var.lambda_zip_name}.zip"
  source = "zips/lambda_function.zip"  # Local path to your ZIP file
}

#Getting latest object that got uploaded via local-exec
data "aws_s3_object" "lambda_function_code" {
  bucket = aws_s3_bucket.lambda_bucket.bucket
  key    = "${var.lambda_zip_name}.zip"
}

resource "aws_lambda_function" "imms_lambda" {
  depends_on  = [null_resource.lambda_typescript_dist,
                aws_s3_object.lambda_function_code
  ]
  s3_bucket=aws_s3_bucket.lambda_bucket.bucket
  s3_key  ="${var.lambda_zip_name}.zip"
  function_name = "${var.prefix}-lambda"
  source_code_hash = data.aws_s3_object.lambda_function_code.etag  # Calculate the hash of the new ZIP file uploaded to s3
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.handler"
  runtime       = "nodejs18.x"
  memory_size   = 1024

  environment {
    variables = {
      "DYNAMODB_TABLE_NAME" : var.dynamodb_table_name
    }
  }
}

output "lambda_function_name" {
  value = aws_lambda_function.imms_lambda.function_name
}
