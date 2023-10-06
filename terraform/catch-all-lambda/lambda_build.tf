data "archive_file" "catch_all_lambda_archive" {
  type        = "zip"
  source_dir  = "${path.module}/catch_all_lambda/src"
  output_path = "build/catch_all_lambda.zip"
}

resource "null_resource" "catch_all_lambda_dist" {
  triggers = {
    token_validator_src = data.archive_file.catch_all_lambda_archive.output_sha
  }

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]

  command = <<EOF
cd ../catch_all_lambda/ && \
# Copy Python files to the dist folder
cp -r ./src/*.py dist/ && \
cd dist && \
# Zip everything in the dist folder and move to terraform directory
zip -r ../../terraform/zips/catch-all.zip . && \
cd ..
aws s3 cp ../terraform/zips/catch-all.zip s3://${aws_s3_bucket.catch_all_lambda_bucket.bucket}/catch-all.zip
EOF
  }
}
