variable "lambda_source_dir" {
  description = "Absolute path to the Lambda source directory"
  type        = string
  default     = "../lambda_typescript"
}

data "archive_file" "catch_all_code_archive" {
  type        = "zip"
  source_dir  = var.lambda_source_dir
  output_path = "build/catch_all_lambda.zip"
}

resource "null_resource" "catch_all_lambda_dist" {
  triggers = {
    token_validator_src = data.archive_file.catch_all_code_archive.output_sha
  }

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]

    command = <<EOF
cd ../catch_all_lambda/ && \
# Copy Python files to the dist folder
cp -r ./src/*.py dist/ && \
cd dist && \
# Zip everything in the dist folder and move to terraform directory
zip -r ../../terraform/zips/catch_all_lambda.zip . && \
cd ..
aws s3 cp ../terraform/zips/catch_all_lambda.zip s3://${aws_s3_bucket.catch_all_lambda_bucket.bucket}/catch_all_lambda.zip
EOF
  }
}
