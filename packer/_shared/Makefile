SHELL := /bin/bash

args =
.DEFAULT_GOAL := build
source_ip := $(shell curl -s ifconfig.co)
account ?= ptl
ptl_account_id := $(shell aws --profile=apm_${account} ssm get-parameter --name /account-ids/ptl --query Parameter.Value --output text)
prod_account_id := $(shell aws --profile=apm_${account} ssm get-parameter --name /account-ids/prod --query Parameter.Value --output text)
dev_account_id := $(shell aws --profile=apm_${account} ssm get-parameter --name /account-ids/dev --query Parameter.Value --output text)

packer := PTL_ACCOUNT_ID=$(ptl_account_id) DEV_ACCOUNT_ID=$(dev_account_id) PROD_ACCOUNT_ID=$(prod_account_id) packer

.INTERMEDIATE: vars/tmp.local.vars

guard-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
		exit 1; \
    fi

print:
	@echo ptl_account_id: \"$(ptl_account_id)\"
	@echo prod_account_id: \"$(prod_account_id)\"
	@echo dev_account_id: \"$(dev_account_id)\"

build:  guard-account
	$(packer) build -var-file=vars/all.vars -var-file=vars/$(account).vars $(args) packer.json

clean-vars:
	@rm -f vars/tmp.local.vars || true

vars/tmp.local.vars:
	@echo "{\"temporary_source_cidr\":\"$(source_ip)/32\"}" > vars/tmp.local.vars

local-vars: clean-vars vars/tmp.local.vars

ip: local-vars
	@cat vars/tmp.local.vars

build-local: guard-account local-vars
	$(packer) build -var-file=vars/all.vars -var-file=vars/$(account).vars -var-file=vars/$(account).local.vars -var-file=vars/tmp.local.vars $(args) packer.json

build-local-any-source-cidr: guard-account
	$(packer) build -var-file=vars/all.vars -var-file=vars/$(account).vars -var-file=vars/$(account).local.vars $(args) packer.json

debug: guard-account
	$(packer) build -debug -var-file=vars/all.vars -var-file=vars/$(account).vars $(args) packer.json

debug-local: guard-account local-vars
	$(packer) build -debug -var-file=vars/all.vars -var-file=vars/$(account).vars -var-file=vars/$(account).local.vars -var-file=vars/tmp.local.vars packer.json $(args)

debug-local-any-source-cidr: guard-account
	$(packer) build -debug -var-file=vars/all.vars -var-file=vars/$(account).vars -var-file=vars/$(account).local.vars $(args) packer.json


