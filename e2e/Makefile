-include .env

APIGEE_ACCESS_TOKEN ?= $(shell export SSO_LOGIN_URL=https://login.apigee.com && eval get_token -u $(APIGEE_USERNAME))
AWS_DOMAIN_NAME=https://$(shell make -C ../terraform -s output name=service_domain_name || true)
IMMS_DELTA_TABLE_NAME=$(shell make -C ../terraform -s output name=imms_delta_table_name || true)

cmd = APIGEE_ACCESS_TOKEN=$(APIGEE_ACCESS_TOKEN) APIGEE_USERNAME=$(APIGEE_USERNAME) IMMS_DELTA_TABLE_NAME=$(IMMS_DELTA_TABLE_NAME) AWS_DOMAIN_NAME=$(AWS_DOMAIN_NAME) poetry run python -m unittest

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

file = immunisation-fhir-api-local
key-pair:
	openssl genrsa -out .keys/$(file).key 4096
	openssl rsa -in .keys/$(file).key -pubout -outform PEM -out .keys/$(file).key.pub
