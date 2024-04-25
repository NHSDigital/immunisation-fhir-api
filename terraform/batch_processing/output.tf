output "container_name" {
    value = local.task_name
}
output "batch_task_arn" {
    value = aws_ecs_task_definition.mock-receiver.arn
}

output "cluster_arn" {
    value = aws_ecs_cluster.batch_processing_cluster.arn
}

output "cluster_name" {
    value = aws_ecs_cluster.batch_processing_cluster.name
}
