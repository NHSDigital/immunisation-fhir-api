output "alb_hostname" {
  value = "${aws_alb.main.dns_name}:3000"
}

output "app_image" {
  description = "The Docker image used for the Grafana application"
  value       = var.app_image
}

# outputs.tf

output "ecs_cluster_id" {
  description = "The ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "ecs_service_name" {
  description = "The name of the ECS service"
  value       = aws_ecs_service.main.name
}

output "ecs_task_definition_arn" {
  description = "The ARN of the ECS task definition"
  value       = aws_ecs_task_definition.app.arn
}

output "ecs_task_definition_family" {
  description = "The family of the ECS task definition"
  value       = aws_ecs_task_definition.app.family
}

output "ecs_task_definition_revision" {
  description = "The revision of the ECS task definition"
  value       = aws_ecs_task_definition.app.revision
}

output "load_balancer_dns" {
  description = "The DNS name of the load balancer"
  value       = aws_alb.main.dns_name
}