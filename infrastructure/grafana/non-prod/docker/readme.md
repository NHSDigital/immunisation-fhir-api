# Docker

## Introduction

This docker folder is used to deploy a grafana docker image to AWS ECR for use by ECS.

## Architecture

1. Dockerfile uses grafana/grafana:latest and is built for linux/amd64 for deploy to ECS
2. Entrypoint script `run.sh` starts grafana in a controlled manner and permits debug on startup

## To Build and deploy Grafana Docker image to AWS ECR

1. Start docker
2. execute `build_push_to_ecr.sh`
3. Success message "Docker image built and pushed to ECR successfully."

The name of the Docker image will depend on the environment, AWS account ID and default region.

_{account_id}.dkr.ecr.{region}.amazonaws.com/imms-{env}-grafana-app:11.0.0-22.04_stable_

e.g.

    345594581768.dkr.ecr.eu-west-2.amazonaws.com/imms-int-grafana-app:11.0.0-22.04_stable

## To test the Grafana Docker image locally

1. Build and deploy as above
2. Pull the Docker image back to your local environment, e.g. for the above example:

    `docker pull 345594581768.dkr.ecr.eu-west-2.amazonaws.com/imms-int-grafana-app:11.0.0-22.04_stable`

3. Run the Docker image in your local environment.

    `docker run -p 3000:3000 345594581768.dkr.ecr.eu-west-2.amazonaws.com/imms-int-grafana-app:11.0.0-22.04_stable`

4. Observe the Grafana dashboard in a web browser.

    `http://localhost:3000`

    The admin login will be as given in the `./grafana.ini` file.

Note that the local image will not display any data, as it is unable to connect to CloudWatch.

## To test the Grafana Docker image remotely

This assumes that your selected environment currently has a working setup on AWS.
For example, the `int` environment uses the following:

ECS cluster: `imms-int-grafana-cluster`

ECS service: `imms-int-grafana-ecs-service`

EC2 load balancer: `imms-int-grafana-alb`

The DNS name of the load balancer is `imms-int-grafana-alb-1548356683.eu-west-2.elb.amazonaws.com`

So:

1.  Update the ECS service to use the new Grafana image, e.g. for the above example:

    `aws ecs update-service --cluster imms-int-grafana-cluster --service imms-int-grafana-ecs-svc --force-new-deployment`

    Note: This may take a couple of minutes to start up the new service task and stop the old one.

2.  Observe the Grafana dashboard in a web browser, e.g.

    `http://imms-int-grafana-alb-1548356683.eu-west-2.elb.amazonaws.com:3000`

---
