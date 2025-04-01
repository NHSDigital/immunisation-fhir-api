-include .env

APIGEE_ACCESS_TOKEN ?= $(shell export SSO_LOGIN_URL=https://login.apigee.com && eval get_token -u $(APIGEE_USERNAME))
AWS_DOMAIN_NAME=https://$(shell make -C ../terraform -s output name=service_domain_name || true)
DYNAMODB_TABLE_NAME=$(shell make -C ../terraform -s output name=dynamodb_table_name || true)
IMMS_DELTA_TABLE_NAME=$(shell make -C ../terraform -s output name=imms_delta_table_name || true)
AWS_SQS_QUEUE_NAME=$(shell make -C ../terraform -s output name=aws_sqs_queue_name || true)
AWS_SNS_TOPIC_NAME=$(shell make -C ../terraform -s output name=aws_sns_topic_name || true)

cmd = APIGEE_ACCESS_TOKEN=$(APIGEE_ACCESS_TOKEN) APIGEE_USERNAME=$(APIGEE_USERNAME) IMMS_DELTA_TABLE_NAME=$(IMMS_DELTA_TABLE_NAME) AWS_DOMAIN_NAME=$(AWS_DOMAIN_NAME) DYNAMODB_TABLE_NAME=$(DYNAMODB_TABLE_NAME) AWS_SQS_QUEUE_NAME=$(AWS_SQS_QUEUE_NAME) AWS_SNS_TOPIC_NAME=$(AWS_SNS_TOPIC_NAME) poetry run python -m unittest

run-mocked-tests:
	$(cmd) discover -v -c -p 'test_create_immunization.py'

# run-immunization:
# 	$(cmd) discover -v -c -p 'test_*_immunization.py'
# # e2e 
# run-delta-immunization:
# 	$(cmd) discover -v -c -p 'test_delta_immunization.py'

# run-authorization:
# 	$(cmd) -v -c test_authorization.py

# run-wait-for-deployment:
# 	$(cmd) -v -c test_deployment.py

# run-proxy:
# 	$(cmd) -v -c test_proxy.py

# run-smoketest:
# 	$(cmd) -c -v -k test_proxy.TestProxyHealthcheck -k test_deployment

# run:
# 	$(cmd)

run-match-%:
	echo "run-match-$*"
	$(cmd) -v -c -k $*

file = immunisation-fhir-api-local
key-pair:
	openssl genrsa -out .keys/$(file).key 4096
	openssl rsa -in .keys/$(file).key -pubout -outform PEM -out .keys/$(file).key.pub
