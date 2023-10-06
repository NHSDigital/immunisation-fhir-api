# Copy the zip archive to an S3 bucket (optional)
resource "aws_s3_bucket" "catch_all_lambda_bucket" {
  bucket = "${var.prefix}-catch-all-lambda-bucket"
}

# Create a null_resource to manage the dependency
resource "null_resource" "catch_all_lambda_dependency" {
  triggers = {
    # Trigger when the zip file is created or its content changes
    zip_file_sha = filesha256(data.archive_file.catch_all_code.output_path)
  }

  provisioner "local-exec" {
    # Copy the zip file to the desired location for your Lambda function
    command = "cp ${data.archive_file.catch_all_code.output_path} ${path.module}/terraform/zips/catch-all.zip"
  }
}

# Upload the zip file to S3 after the zip file is created
resource "aws_s3_object" "catch_all_function_code" {
  bucket = aws_s3_bucket.catch_all_lambda_bucket.bucket
  key    = "catch-all.zip"
  source = null_resource.catch_all_lambda_dependency.triggers["zip_file_sha"] == filesha256(data.archive_file.catch_all_code.output_path) ? data.archive_file.catch_all_code.output_path : null
}

# Create the Lambda function after the zip file is uploaded to S3
resource "aws_lambda_function" "catch_all_lambda" {
  depends_on  = [aws_s3_object.catch_all_function_code]
  
  s3_bucket    = aws_s3_bucket.catch_all_lambda_bucket.bucket
  s3_key       = "catch-all.zip"
  function_name = "${var.prefix}-catch-all-lambda"
  handler      = "catch-all.handler"
  runtime      = "python3.8"  # Assuming your Python script is compatible with this runtime
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
