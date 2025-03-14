# main.tf 
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "3.0.2"
    }
    template = {
      source  = "hashicorp/template"
      version = "~> 2.2.0"
    }
  }
  backend "s3" {
    region = "eu-west-2"
    key    = "state"
  }
  required_version = ">= 1.5.0"
}

provider "aws" {
  region  = var.aws_region
  profile = "apim-dev"
  default_tags {
    tags = var.tags
  }
}

provider "aws" {
  alias   = "acm_provider"
  region  = var.aws_region
  profile = "apim-dev"
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
############################################################################################################


# alb.tf

resource "aws_alb" "main" {
  name            = "${var.prefix}-alb"
  subnets         = aws_subnet.grafana_public.*.id
  security_groups = [aws_security_group.lb.id]
}

resource "aws_alb_target_group" "app" {
  name        = "${var.prefix}-alb-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.grafana_main.id
  target_type = "ip"

  health_check {
    healthy_threshold   = 3
    interval            = 30
    protocol            = "HTTP"
    matcher             = "200"
    timeout             = 3
    path                = var.health_check_path
    unhealthy_threshold = 2
  }
}

# Redirect all traffic from the ALB to the target group
resource "aws_alb_listener" "front_end" {
  load_balancer_arn = aws_alb.main.id
  port              = var.app_port
  protocol          = "HTTP"
  default_action {
    target_group_arn = aws_alb_target_group.app.id
    type             = "forward"
  }

  tags = merge(var.tags, {
    Name = "${var.prefix}-alb-listener"
  })
}
############################################################################################################
# auto_scaling.tf

resource "aws_appautoscaling_target" "target" {
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.main.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  role_arn           = aws_iam_role.ecs_auto_scale_role.arn
  min_capacity       = 1
  max_capacity       = 1
  tags = merge(var.tags, {
    Name = "${var.prefix}-aas-tgt"
  })
}

# Automatically scale capacity up by one
resource "aws_appautoscaling_policy" "up" {
  name               = "grafana_scale_up"
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.main.name}"
  scalable_dimension = "ecs:service:DesiredCount"

  step_scaling_policy_configuration {
    adjustment_type         = "ChangeInCapacity"
    cooldown                = 60
    metric_aggregation_type = "Maximum"

    step_adjustment {
      metric_interval_lower_bound = 0
      scaling_adjustment          = 1
    }
  }

  depends_on = [aws_appautoscaling_target.target]

}

# Automatically scale capacity down by one
resource "aws_appautoscaling_policy" "down" {
  name               = "grafana_scale_down"
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.main.name}"
  scalable_dimension = "ecs:service:DesiredCount"

  step_scaling_policy_configuration {
    adjustment_type         = "ChangeInCapacity"
    cooldown                = 60
    metric_aggregation_type = "Maximum"

    step_adjustment {
      metric_interval_lower_bound = 0
      scaling_adjustment          = -1
    }
  }

  depends_on = [aws_appautoscaling_target.target]
}
############################################################################################################
# ecs.tf
# ecs.tf

resource "aws_ecs_cluster" "main" {
    name = "grafana-cluster"
}

data "template_file" "grafana_app" {
    template = file("${path.module}/templates/ecs/grafana_app.json.tpl")

    vars = {
        app_image      = var.app_image
        app_port       = var.app_port
        fargate_cpu    = var.fargate_cpu
        fargate_memory = var.fargate_memory
        aws_region     = var.aws_region
    }
}

resource "aws_ecs_task_definition" "app" {
    family                   = "grafana-app-task"
    execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
    network_mode             = "awsvpc"
    requires_compatibilities = ["FARGATE"]
    cpu                      = var.fargate_cpu
    memory                   = var.fargate_memory
    container_definitions    = data.template_file.grafana_app.rendered
    tags = merge(var.tags, {
        Name = "${var.prefix}-ecs-task"
    })
}

resource "aws_ecs_service" "main" {
    name            = "${var.prefix}-ecs-svc"
    cluster         = aws_ecs_cluster.main.id
    task_definition = aws_ecs_task_definition.app.arn
    desired_count   = var.app_count
    launch_type     = "FARGATE"

    network_configuration {
        security_groups  = [aws_security_group.ecs_tasks.id]
        subnets          = aws_subnet.grafana_private.*.id
        assign_public_ip = true
    }

    load_balancer {
        target_group_arn = aws_alb_target_group.app.id
        container_name   = "grafana-app"
        container_port   = var.app_port
    }

    depends_on = [aws_alb_listener.front_end, aws_iam_role_policy_attachment.ecs-task-execution-role-policy-attachment]
}
############################################################################################################
# iam.tf
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.prefix}-ecs-task-execution-role"

  assume_role_policy = <<EOF
{
 "Version": "2012-10-17",
 "Statement": [
   {
     "Action": "sts:AssumeRole",
     "Principal": {
       "Service": "ecs-tasks.amazonaws.com"
     },
     "Effect": "Allow",
     "Sid": ""
   }
 ]
}
EOF
}

resource "aws_iam_role" "ecs_task_role" {
  name = "${var.prefix}-ecs-task-role"

  assume_role_policy = <<EOF
{
 "Version": "2012-10-17",
 "Statement": [
   {
     "Action": "sts:AssumeRole",
     "Principal": {
       "Service": "ecs-tasks.amazonaws.com"
     },
     "Effect": "Allow",
     "Sid": ""
   }
 ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "ecs-task-execution-role-policy-attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "task_s3" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

data "aws_iam_policy_document" "ecs_auto_scale_role" {
  version = "2012-10-17"
  statement {
    effect = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["application-autoscaling.amazonaws.com"]
    }
  }
}

# ECS auto scale role
resource "aws_iam_role" "ecs_auto_scale_role" {
  name               = var.ecs_auto_scale_role_name
  assume_role_policy = data.aws_iam_policy_document.ecs_auto_scale_role.json
}

# ECS auto scale role policy attachment
resource "aws_iam_role_policy_attachment" "ecs_auto_scale_role" {
  role       = aws_iam_role.ecs_auto_scale_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceAutoscaleRole"
}

# Monitoring role
resource "aws_iam_role" "monitoring_role" {
  name = "${var.prefix}-monitoring-role"

  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "ecs-tasks.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "monitoring_policy" {
  name   = "${var.prefix}-monitoring-policy"
  role   = aws_iam_role.monitoring_role.id

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowReadingMetricsFromCloudWatch",
        "Effect": "Allow",
        "Action": [
          "cloudwatch:DescribeAlarmsForMetric",
          "cloudwatch:DescribeAlarmHistory",
          "cloudwatch:DescribeAlarms",
          "cloudwatch:ListMetrics",
          "cloudwatch:GetMetricData",
          "cloudwatch:GetInsightRuleReport"
        ],
        "Resource": "*"
      },
      {
        "Sid": "AllowReadingResourceMetricsFromPerformanceInsights",
        "Effect": "Allow",
        "Action": "pi:GetResourceMetrics",
        "Resource": "*"
      },
      {
        "Sid": "AllowReadingLogsFromCloudWatch",
        "Effect": "Allow",
        "Action": [
          "logs:DescribeLogGroups",
          "logs:GetLogGroupFields",
          "logs:StartQuery",
          "logs:StopQuery",
          "logs:GetQueryResults",
          "logs:GetLogEvents"
        ],
        "Resource": "*"
      },
      {
        "Sid": "AllowReadingTagsInstancesRegionsFromEC2",
        "Effect": "Allow",
        "Action": [
          "ec2:DescribeTags",
          "ec2:DescribeInstances",
          "ec2:DescribeRegions"
        ],
        "Resource": "*"
      },
      {
        "Sid": "AllowReadingResourcesForTags",
        "Effect": "Allow",
        "Action": "tag:GetResources",
        "Resource": "*"
      }
    ]
  })
}
############################################################################################################
# network.tf

# Fetch AZs in the current region
data "aws_availability_zones" "available" {}

resource "aws_vpc" "grafana_main" {
    cidr_block = "172.18.0.0/16"
    tags = {
        Name = "${var.prefix}-vpc"
    }
}

# Create var.az_count private subnets, each in a different AZ
resource "aws_subnet" "grafana_private" {
    count             = var.az_count
    cidr_block        = cidrsubnet(aws_vpc.grafana_main.cidr_block, 8, count.index)
    availability_zone = data.aws_availability_zones.available.names[count.index]
    vpc_id            = aws_vpc.grafana_main.id
    tags = merge(var.tags, {
        Name = "${var.prefix}-private-subnet-${count.index}"
    })
}

# Create var.az_count public subnets, each in a different AZ
resource "aws_subnet" "grafana_public" {
    count                   = var.az_count
    cidr_block              = cidrsubnet(aws_vpc.grafana_main.cidr_block, 8, var.az_count + count.index)
    availability_zone       = data.aws_availability_zones.available.names[count.index]
    vpc_id                  = aws_vpc.grafana_main.id
    map_public_ip_on_launch = true
    tags = merge(var.tags, {
        Name = "${var.prefix}-public-subnet-${count.index}"
    })
}

# Internet Gateway for the public subnet
resource "aws_internet_gateway" "gw" {
    vpc_id = aws_vpc.grafana_main.id
    tags = merge(var.tags, {
        Name = "${var.prefix}-igw"
    })
}

# Route the public subnet traffic through the IGW
resource "aws_route" "internet_access" {
    route_table_id         = aws_vpc.grafana_main.main_route_table_id
    destination_cidr_block = "0.0.0.0/0"
    gateway_id             = aws_internet_gateway.gw.id    
}

# Create a new route table for the private subnets
resource "aws_route_table" "private" {
    count  = var.az_count
    vpc_id = aws_vpc.grafana_main.id
    tags = merge(var.tags, {
        Name = "${var.prefix}-private-rt-${count.index}"
    })
}

# Explicitly associate the newly created route tables to the private subnets (so they don't default to the main route table)
resource "aws_route_table_association" "private" {
    count          = var.az_count
    subnet_id      = element(aws_subnet.grafana_private.*.id, count.index)
    route_table_id = element(aws_route_table.private.*.id, count.index)
}

# Security group for VPC endpoints
resource "aws_security_group" "vpc_endpoints" {
    name        = "vpc-endpoints-sg"
    description = "Security group for VPC endpoints"
    vpc_id      = aws_vpc.grafana_main.id

    ingress {
        from_port   = 443
        to_port     = 443
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }

    egress {
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }
    tags = merge(var.tags, {
        Name = "${var.prefix}-vpc-endpoints-sg"
    })
}

# Create VPC Endpoint for ECR API
resource "aws_vpc_endpoint" "ecr_api" {
    vpc_id            = aws_vpc.grafana_main.id
    service_name      = "com.amazonaws.${var.aws_region}.ecr.api"
    vpc_endpoint_type = "Interface"
    subnet_ids        = aws_subnet.grafana_private.*.id
    security_group_ids = [aws_security_group.vpc_endpoints.id]
    tags = merge(var.tags, {
        Name = "${var.prefix}-ecr-api-vpce"
    })
}

# Create VPC Endpoint for ECR Docker
resource "aws_vpc_endpoint" "ecr_docker" {
    vpc_id            = aws_vpc.grafana_main.id
    service_name      = "com.amazonaws.${var.aws_region}.ecr.dkr"
    vpc_endpoint_type = "Interface"
    subnet_ids        = aws_subnet.grafana_private.*.id
    security_group_ids = [aws_security_group.vpc_endpoints.id]
    tags = merge(var.tags, {
        Name = "${var.prefix}-ecr-dkr-vpce"
    })
}

# Create VPC Endpoint for CloudWatch Logs
resource "aws_vpc_endpoint" "cloudwatch_logs" {
    vpc_id            = aws_vpc.grafana_main.id
    service_name      = "com.amazonaws.${var.aws_region}.logs"
    vpc_endpoint_type = "Interface"
    subnet_ids        = aws_subnet.grafana_private.*.id
    security_group_ids = [aws_security_group.vpc_endpoints.id]
    tags = merge(var.tags, {
        Name = "${var.prefix}-cloudwatch-logs-vpce"
    })
}
############################################################################################################
# security.tf
# security.tf

# ALB security Group: Edit to restrict access to the application
resource "aws_security_group" "lb" {
    name        = "grafana-load-balancer-security-group"
    description = "controls access to the ALB"
    vpc_id      = aws_vpc.grafana_main.id

    ingress {
        protocol    = "tcp"
        from_port   = var.app_port
        to_port     = var.app_port
        cidr_blocks = ["0.0.0.0/0"]
    }

    egress {
        protocol    = "-1"
        from_port   = 0
        to_port     = 0
        cidr_blocks = ["0.0.0.0/0"]
    }
    tags = merge(var.tags, {
        Name = "${var.prefix}-sg-lb"
    })
}

# Traffic to the ECS cluster should only come from the ALB
resource "aws_security_group" "ecs_tasks" {
    name        = "cb-ecs-tasks-security-group"
    description = "allow inbound access from the ALB only"
    vpc_id      = aws_vpc.grafana_main.id

    ingress {
        protocol        = "tcp"
        from_port       = var.app_port
        to_port         = var.app_port
        security_groups = [aws_security_group.lb.id]
    }

    egress {
        protocol    = "-1"
        from_port   = 0
        to_port     = 0
        cidr_blocks = ["0.0.0.0/0"]
    }
    tags = merge(var.tags, {
        Name = "${var.prefix}-sg-ecs-tasks"
    })
}
############################################################################################################
#logs.tf
# logs.tf

# Set up CloudWatch group and log stream and retain logs for 30 days
resource "aws_cloudwatch_log_group" "grafana_log_group" {
  name              = "/ecs/grafana-app"
  retention_in_days = 30

  tags = merge(var.tags, {
      Name = "${var.prefix}-log-group"
  })
}

resource "aws_cloudwatch_log_stream" "grafana_log_group" {
  name           = "${var.prefix}-log-stream"
  log_group_name = aws_cloudwatch_log_group.grafana_log_group.name
}


############################################################

# outputs.tf

output "alb_hostname" {
  value = "${aws_alb.main.dns_name}:3000"
}

output "app_image" {
  description = "The Docker image used for the Grafana application"
  value       = var.app_image
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