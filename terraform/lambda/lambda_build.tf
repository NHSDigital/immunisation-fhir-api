data "aws_caller_identity" "current" {}
data "archive_file" "lambda_typescript_archive" {
  type        = "zip"
  source_dir  = "${path.root}/../lambda_typescript"
  output_path = "build/lambda_typescript.zip"
}

resource "null_resource" "lambda_typescript_dist" {
  triggers = {
    token_validator_src = data.archive_file.lambda_typescript_archive.output_sha
  }

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]

    command = <<EOF
  aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.eu-west-2.amazonaws.com
  cd ../lambda_typescript/ && \
  # Run the npm commands to transpile the TypeScript to JavaScript
  npm i && \
  npm run build && \
  npm prune --production &&\
  
  # Create a dist folder and copy only the js files to distribution.
  # AWS Lambda does not have a use for a package.json or typescript files on runtime.
  mkdir dist &&\
  cp -r ./src/*.js dist/ &&\
  cp -r ./node_modules dist/ &&\
  cd dist &&\
  find . -name "*.zip" -type f -delete && \
  #Create zips directory under terraform, delete existing one
  rm -rf ../../terraform/zips
  mkdir ../../terraform/zips
  # Zip everything in the dist folder and move to terraform directory
  zip -r ../../terraform/zips/${var.lambda_zip_name}.zip . && \
  #Delete Distibution folder
  cd .. && rm -rf dist
  aws s3 cp ../terraform/zips/${var.lambda_zip_name}.zip s3://${aws_s3_bucket.lambda_bucket.bucket}/${var.lambda_zip_name}.zip
   EOF
       
  }
}