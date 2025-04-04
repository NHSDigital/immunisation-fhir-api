############################################################

# outputs.tf

output "alb_hostname" {
  value = "${aws_alb.main.dns_name}:3000"
}

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

// output the url to access the grafana app
output "grafana_url" {
  value = "http://${aws_alb.main.dns_name}:${var.app_port}"
}

output "alb_target_group_arn" {
  description = "The ARN of the ALB target group"
  value       = aws_alb_target_group.app.arn
}

output "alb_listener_arn" {
  description = "The ARN of the ALB listener"
  value       = aws_alb_listener.front_end.arn
}

output "prefix" {
    value = local.prefix
}

output "app_image" {
    value = local.app_image
}

output "app_name" {
    value = local.app_name
}

output "Monitoring_Role_Arn" {
    value = aws_iam_role.monitoring_role.arn
}

