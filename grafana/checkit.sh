#!/bin/bash

# Set your variables
CLUSTER_NAME="grafana-cluster"
SERVICE_NAME="imms-fhir-api-grafana-ecs-svc"
VPC_ID="vpc-03fd332ae0ff69096"
SECURITY_GROUP_ID1="sg-0436b045091912df1"
SECURITY_GROUP_ID2="sg-00dec8ab50df5953c"
SECURITY_GROUP_ID3="sg-0dcba2dabd54be6f2"
LOAD_BALANCER_NAME="imms-fhir-api-grafana-alb"
TARGET_GROUP_NAME="imms-fhir-api-grafana-alb-tg"
LOG_GROUP_NAME="imms-fhir-api-grafana-log-group"

# Verify ECS Service and Task Status
echo "Checking ECS service and task status..."
# aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME
aws ecs describe-services --cluster grafana-cluster --services imms-fhir-api-grafana-ecs-svc

TASK_ID=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --query 'taskArns[0]' --output text)
aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ID

# Check VPC and Subnet Configuration
echo "Checking VPC and subnet configuration..."
aws ec2 describe-vpcs --vpc-ids $VPC_ID
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID"

# Verify Security Groups
echo "Checking security groups..."
aws ec2 describe-security-groups --group-ids $SECURITY_GROUP_ID1 $SECURITY_GROUP_ID2 $SECURITY_GROUP_ID3

# Check Load Balancer Configuration
echo "Checking load balancer configuration..."
aws elbv2 describe-load-balancers --names $LOAD_BALANCER_NAME
TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups --names $TARGET_GROUP_NAME --query 'TargetGroups[0].TargetGroupArn' --output text)
aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN

# Access Grafana
echo "Accessing Grafana..."
LOAD_BALANCER_DNS=$(aws elbv2 describe-load-balancers --names $LOAD_BALANCER_NAME --query 'LoadBalancers[0].DNSName' --output text)
echo "Grafana is accessible at http://$LOAD_BALANCER_DNS:3000"

# Check Logs
echo "Checking logs..."
# LOG_STREAM_NAME=$(aws logs describe-log-streams --log-group-name $LOG_GROUP_NAME --query 'logStreams[0].logStreamName' --output text)
LOG_STREAM_NAME=$(aws logs describe-log-streams --log-group-name /ecs/grafana-app --query 'logStreams[0].logStreamName' --output text)

aws logs get-log-events --log-group-name $LOG_GROUP_NAME --log-stream-name $LOG_STREAM_NAME

echo "Check completed."

# grafana at http://imms-fhir-api-grafana-alb-1804257202.eu-west-2.elb.amazonaws.com:3000