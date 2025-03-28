# alb.tf

resource "aws_alb" "main" {
  name            = "${local.prefix}-alb"
  subnets         = aws_subnet.grafana_public[*].id
  security_groups = [aws_security_group.lb.id]
}

resource "aws_alb_target_group" "app" {
  name        = "${local.prefix}-tg"
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
    path                =  "/api/health" # Grafana health check endpoint
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
    Name = "${local.prefix}-alb-listener"
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
    Name = "${local.prefix}-aas-tgt"
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
    name = "${local.prefix}-cluster"
}

data "template_file" "grafana_app" {
    template = file("${path.module}/templates/ecs/grafana_app.json.tpl")

    vars = {
        app_image      = local.app_image
        app_name       = local.app_name
        app_port       = var.app_port
        fargate_cpu    = var.fargate_cpu
        fargate_memory = var.fargate_memory
        aws_region     = var.aws_region
        log_group      = local.log_group
        health_check_path = var.health_check_path
    }
}

resource "aws_ecs_task_definition" "app" {
    family                   = "${local.prefix}-app"
    execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
    task_role_arn            = aws_iam_role.ecs_task_role.arn    
    network_mode             = "awsvpc"
    requires_compatibilities = ["FARGATE"]
    cpu                      = var.fargate_cpu
    memory                   = var.fargate_memory
    container_definitions    = data.template_file.grafana_app.rendered
    tags = merge(var.tags, {
        Name = "${local.prefix}-task"
    })

}

resource "aws_ecs_service" "main" {
  name            = "${local.prefix}-ecs-svc"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.app_count
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.grafana_private[*].id
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_alb_target_group.app.id
    container_name   = local.app_name
    container_port   = var.app_port
  }
}
############################################################################################################
# iam.tf
resource "aws_iam_policy" "route53resolver_policy" {
  name        = "${local.prefix}-route53resolver-policy"
  description = "Policy to allow Route 53 Resolver DNS Firewall actions"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "route53resolver:ListFirewallRuleGroupAssociations",
          "route53resolver:ListFirewallRuleGroups",
          "route53resolver:ListFirewallRules"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "route53resolver_policy_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.route53resolver_policy.arn
}

## Task Execution Role (ecs_task_execution_role):
## This role is used by the ECS agent to pull container images from 
## Amazon ECR, and to store and retrieve logs in Amazon CloudWatch.
## It grants permissions needed for ECS to start and manage tasks
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${local.prefix}-ecs-task-execution-role"

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

resource "aws_iam_policy" "ecs_task_execution_policy" {
  name        = "${local.prefix}-ecs-task-execution-policy"
  description = "Policy for ECS task execution role to access ECR and CloudWatch Logs"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
  "Action": [
    "ecr:GetDownloadUrlForLayer",
    "ecr:BatchGetImage",
    "ecr:BatchCheckLayerAvailability",
    "ecr:GetAuthorizationToken",
        "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents",
    "s3:*"
  ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ecs_task_execution_policy.arn
}


resource "aws_iam_role_policy_attachment" "ecs-task-execution-role-policy-attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# This role is assumed by the containers running within the task.
# It grants permissions that the application inside the container 
# needs to interact with other AWS services (e.g., accessing S3, 
# DynamoDB, etc.).
resource "aws_iam_role" "ecs_task_role" {
  name = "${local.prefix}-ecs-task-role"

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

        # Resource = ${aws_iam_role.monitoring_role.arn}


resource "aws_iam_policy" "ecs_task_policy" {
  name        = "${local.prefix}-ecs-task-policy"
  description = "Policy for ECS task role to access CloudWatch Logs"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
           "logs:CreateLogStream",
           "logs:PutLogEvents",
         ],
        Resource = "*"
      }
    ]
  })
}
resource "aws_iam_role_policy_attachment" "task_logs" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_task_policy.arn
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
  name = "${local.prefix}-ecs_role"
  assume_role_policy = data.aws_iam_policy_document.ecs_auto_scale_role.json
}
# ECS auto scale role policy attachment
resource "aws_iam_role_policy_attachment" "ecs_auto_scale_role" {
  role       = aws_iam_role.ecs_auto_scale_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceAutoscaleRole"
}

# Monitoring role
resource "aws_iam_role" "monitoring_role" {

  name = "${local.prefix}-monitoring-role"

  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "sts:AssumeRole",
        "Principal": {
          "Service": "ecs-tasks.amazonaws.com"
        }
      },
      {
        Effect = "Allow",
        Principal = {
          AWS = aws_iam_role.ecs_task_role.arn
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "monitoring_policy" {
  name   = "${local.prefix}-monitoring-policy"
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
          "logs:DescribeLogStreams",
          "logs:GetLogEvents",
          "logs:FilterLogEvents",
          "logs:GetLogGroupFields",
          "logs:StartQuery",
          "logs:StopQuery",
          "logs:GetQueryResults"
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
    cidr_block = var.cidr_block
    // enable dns resolution
    enable_dns_support = true
    enable_dns_hostnames = true
    tags = {
        Name = "${local.prefix}-vpc"
    }
}


# Create var.az_count private subnets, each in a different AZ
resource "aws_subnet" "grafana_private" {
    count             = var.az_count
    cidr_block        = cidrsubnet(aws_vpc.grafana_main.cidr_block, 8, count.index)
    availability_zone = data.aws_availability_zones.available.names[count.index]
    vpc_id            = aws_vpc.grafana_main.id
    tags = merge(var.tags, {
        Name = "${local.prefix}-private-subnet-${count.index}"
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
        Name = "${local.prefix}-public-subnet-${count.index}"
    })
}


# Internet Gateway for the public subnet
resource "aws_internet_gateway" "gw" {
    vpc_id = aws_vpc.grafana_main.id
    tags = merge(var.tags, {
        Name = "${local.prefix}-igw"
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
        Name = "${local.prefix}-private-rt-${count.index}"
    })
}

# Route the private subnet traffic through the NAT Gateway
resource "aws_route" "private_nat_gateway" {
  count          = var.az_count
  route_table_id = element(aws_route_table.private[*].id, count.index)
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat.id
}


# Explicitly associate the newly created route tables to the private subnets (so they don't default to the main route table)
resource "aws_route_table_association" "private" {
    count          = var.az_count
    subnet_id      = element(aws_subnet.grafana_private[*].id, count.index)
    route_table_id = element(aws_route_table.private[*].id, count.index)
}


############################################################################################################
# security.tf

# Security group for the ALB
resource "aws_security_group" "lb" {
  name        = "grafana-load-balancer-security-group" # @TODO ${local.prefix}-alb-sg"
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
    Name = "${local.prefix}-alb-sg"
  })
}

# Security group for ECS tasks
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
    Name = "${local.prefix}-sg-ecs-tasks"
  })
}

# Elastic IP & NAT Gateway for egress traffic
resource "aws_eip" "nat" {
  domain = "vpc"
  tags = merge(var.tags, {
    Name = "${local.prefix}-nat-eip"
  })
}


resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = element(aws_subnet.grafana_public[*].id, 0) 
  tags = merge(var.tags, {
    Name = "${local.prefix}-nat-gw"
  })
}