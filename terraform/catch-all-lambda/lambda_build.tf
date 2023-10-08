variable "lambda_source_dir" {
  description = "Absolute path to the Lambda source directory"
  type        = string
  default     = "../catch_all_lambda"
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
mkdir -p dist && \
cp -r ./src/catch-all.py dist/ && \
cd dist && \
zip -r ../../terraform/zips/catch_all_lambda.zip . && \
cd ..
rm -rf dist
aws s3 cp ../../terraform/zips/catch_all_lambda.zip s3://immunisation-fhir-api-pr-36-catch-all-lambda-bucket/catch_all_lambda.zip
EOF
  }
}
