resource "aws_ecr_repository" "batch_processing_repository" {
    name = local.prefix
}
