resource "aws_s3_bucket" "catch_all_lambda_bucket" {
  bucket        = "${var.prefix}-catch-all-lambda-bucket"
  force_destroy = true
}

#Upload object for the first time, then it gets updated via local-exec
resource "aws_s3_object" "catch_all_function_code" {
  bucket = aws_s3_bucket.catch_all_lambda_bucket.bucket
  key    = "catch-all.zip"
  source = "zips/catch-all.zip"  # Local path to your ZIP file
}

#Getting latest object that got uploaded via local-exec
data "aws_s3_object" "catch_all_lambda" {
  bucket = aws_s3_bucket.catch_all_lambda_bucket.bucket
  key    = "catch-all.zip"
}

resource "aws_lambda_function" "catch_all_lambda" {
  depends_on  = [null_resource.lambda_typescript_dist,
                aws_s3_object.catch_all_function_code
  ]
  s3_bucket=aws_s3_bucket.catch_all_lambda_bucket.bucket
  s3_key  ="catch-all.zip"
  function_name = "${var.prefix}-catch-all-lambda"
  handler      = "catch-all.handler"  
  runtime      = "nodejs14.x"    
  role         = aws_iam_role.lambda_role.arn
  timeout      = 10
  memory_size  = 1024
}

output "catch_all_name" {
  value = aws_lambda_function.catch_all_lambda.function_name
}