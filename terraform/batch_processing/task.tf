locals {
    task_name = "batch_processing"
    image_tag = "latest"
}
resource "aws_ecs_task_definition" "mock-receiver" {
    family                   = local.prefix
    network_mode             = "awsvpc"
    // ARN of IAM role that allows your Amazon ECS container task to make calls to other AWS services.
    task_role_arn            = aws_iam_role.task_role.arn
    //ARN of the task execution role that the Amazon ECS container agent and the Docker daemon can assume.
    execution_role_arn       = aws_iam_role.task_execution_role.arn
    requires_compatibilities = ["FARGATE"]
    cpu                      = 256
    memory                   = 512
    runtime_platform {
        operating_system_family = "LINUX"
        cpu_architecture        = "X86_64"
    }

    container_definitions = jsonencode([
        {
            name      = local.task_name
            image     = "${aws_ecr_repository.batch_processing_repository.repository_url}:${local.image_tag}"
            essential = true

            logConfiguration : {
                "logDriver" : "awslogs",
                "options" : {
                    "awslogs-group" : aws_cloudwatch_log_group.batch_task_log_group.name
                    "awslogs-region" : "eu-west-2",
                    "awslogs-stream-prefix" : "batch"
                }
            }
        }
    ])
}


