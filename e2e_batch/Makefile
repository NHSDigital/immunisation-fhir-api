-include .env

APIGEE_ACCESS_TOKEN ?= $(shell export SSO_LOGIN_URL=https://login.apigee.com && eval get_token -u $(APIGEE_USERNAME))
AWS_DOMAIN_NAME=https://$(shell make -C ../terraform -s output name=service_domain_name || true)
PARALLEL_WORKERS=2

print-token:
	@echo "APIGEE_ACCESS_TOKEN=$(APIGEE_ACCESS_TOKEN)"


run-immunization-batch:
	ENVIRONMENT=$(ENVIRONMENT) poetry run python -m unittest -v -c

test:
	ENVIRONMENT=$(ENVIRONMENT) time poetry run python -m unittest -v -c

testp1:
	ENVIRONMENT=$(ENVIRONMENT) time poetry run unittest-parallel -v -j $(PARALLEL_WORKERS)

testp2:
	ENVIRONMENT=$(ENVIRONMENT) time poetry run pytest -n $(PARALLEL_WORKERS) -v -s
