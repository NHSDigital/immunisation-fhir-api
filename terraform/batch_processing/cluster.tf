resource "aws_ecs_cluster" "batch_processing_cluster" {
    name = "${var.short_prefix}_batch_processing"
}
