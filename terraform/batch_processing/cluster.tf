resource "aws_ecs_cluster" "batch_processing_cluster" {
    name = "${var.prefix}_batch_processing"
}
