# Copy the zip archive to an S3 bucket (optional)
resource "aws_s3_bucket" "catch_all_lambda_bucket" {
  bucket = "${var.prefix}-catch-all-lambda-bucket"
  force_destroy = true
}

# Upload the zip file to S3 after the zip file is created
resource "aws_s3_object" "catch_all_function_code" {
  bucket = aws_s3_bucket.catch_all_lambda_bucket.bucket
  key    = "catch-all.zip"
  source = "zips/catch_all_lambda.zip"
}

# Create the Lambda function after the zip file is uploaded to S3
resource "aws_lambda_function" "catch_all_lambda" {
  depends_on  = [aws_s3_object.catch_all_function_code]
  
  s3_bucket    = aws_s3_bucket.catch_all_lambda_bucket.bucket
  s3_key       = "catch-all.zip"
  function_name = "${var.prefix}-catch-all-lambda"
  handler      = "catch-all.handler"
  runtime      = "nodejs18.x"  # Assuming your Python script is compatible with this runtime
  role         = aws_iam_role.catch_all_lambda_role.arn
  timeout      = 10
  memory_size  = 1024
}

output "catch_all_lambda_name" {
  value = aws_lambda_function.catch_all_lambda.function_name
}

output "catch_all_lambda_arn" {
  value = aws_lambda_function.catch_all_lambda.arn
}
