-include .env

AWS_DOMAIN_NAME=https://internal-dev.imms.dev.vds.platform.nhs.uk
DYNAMODB_TABLE_NAME=imms-internal-dev-imms-events
IMMS_DELTA_TABLE_NAME=imms-internal-dev-delta
AWS_SQS_QUEUE_NAME=imms-internal-dev-delta-dlq
AWS_SNS_TOPIC_NAME=imms-internal-dev-delta-sns

cmd = APIGEE_ACCESS_TOKEN=$(APIGEE_ACCESS_TOKEN) APIGEE_USERNAME=$(APIGEE_USERNAME) IMMS_DELTA_TABLE_NAME=$(IMMS_DELTA_TABLE_NAME) AWS_DOMAIN_NAME=$(AWS_DOMAIN_NAME) DYNAMODB_TABLE_NAME=$(DYNAMODB_TABLE_NAME) AWS_SQS_QUEUE_NAME=$(AWS_SQS_QUEUE_NAME) AWS_SNS_TOPIC_NAME=$(AWS_SNS_TOPIC_NAME) poetry run python -m unittest

run-immunization:
	$(cmd) discover -v -c -p 'test_*_immunization.py'

run-delta-immunization:
	$(cmd) discover -v -c -p 'test_delta_immunization.py'

run-authorization:
	$(cmd) -v -c test_authorization.py

run-wait-for-deployment:
	$(cmd) -v -c test_deployment.py

run-proxy:
	$(cmd) -v -c test_proxy.py

run-smoketest:
	$(cmd) -c -v -k test_proxy.TestProxyHealthcheck -k test_deployment

run:
	$(cmd)

run-match-%:
	$(cmd) -v -c -k $*

file = immunisation-fhir-api-local
key-pair:
	openssl genrsa -out .keys/$(file).key 4096
	openssl rsa -in .keys/$(file).key -pubout -outform PEM -out .keys/$(file).key.pub
