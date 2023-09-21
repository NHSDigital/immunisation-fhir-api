locals {
    // Flag so we can force delete s3 buckets with items in for pr and shortcode environments only.
    is_temp = length(regexall("[a-z]{2,4}-?[0-9]+", var.environment)) > 0
}

resource "aws_s3_bucket" "batch_lambda_source_bucket" {
    bucket = "${var.prefix}-batch-lambda-source"
    force_destroy = local.is_temp
}

resource "aws_s3_bucket" "batch_lambda_destination_bucket" {
    bucket = "${var.prefix}-batch-lambda-destination"
    force_destroy = local.is_temp
}

resource "aws_s3_bucket_notification" "batch_processing_source_lambda_trigger" {
    bucket = "${aws_s3_bucket.batch_lambda_source_bucket.id}"
    lambda_function {
        lambda_function_arn = "${aws_lambda_function.batch_processing_lambda.arn}"
        events = ["s3:ObjectCreated:*"]
    }
    depends_on = [ aws_lambda_permission.allow_terraform_bucket ]
}
