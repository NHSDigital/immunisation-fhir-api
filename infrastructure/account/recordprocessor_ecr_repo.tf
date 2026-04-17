resource "aws_ecr_repository" "recordprocessor_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  image_tag_mutability = "IMMUTABLE"
  name                 = "imms-recordprocessor-repo"
}