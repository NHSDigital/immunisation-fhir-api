SHELL=/usr/bin/env bash -euo pipefail

PYTHON_PROJECT_DIRS_WITH_UNIT_TESTS = backend batch_processor_filter delta_backend filenameprocessor mesh_processor recordprocessor lambdas/ack_backend lambdas/redis_sync lambdas/id_sync lambdas/mns_subscription lambdas/shared
PYTHON_PROJECT_DIRS = e2e e2e_batch $(PYTHON_PROJECT_DIRS_WITH_UNIT_TESTS)

#Installs dependencies using poetry.
install-python:
	poetry lock --no-update
	poetry install

#Installs dependencies using npm.
install-node:
	npm install --legacy-peer-deps

#Configures Git Hooks, which are scripts that run given a specified event.
.git/hooks/pre-commit:
	cp scripts/pre-commit .git/hooks/pre-commit

#Condensed Target to run all targets above.
install: install-node install-python .git/hooks/pre-commit

#Run the npm linting script (specified in package.json). Used to check the syntax and formatting of files.
lint:
	npm run lint

#Removes build/ + dist/ directories
clean:
	rm -rf build
	rm -rf dist

#Creates the fully expanded OAS spec in json
publish: clean
	mkdir -p build
	npm run publish 2> /dev/null
	cp build/immunisation-fhir-api.json sandbox/
	cp -r specification sandbox/specification

#Runs build proxy script
build-proxy:
	scripts/build_proxy.sh

#Files to loop over in release
# VED-811: remove everything except for proxy related files as we move to Github Actions for backend deployment
_dist_include="pytest.ini poetry.lock poetry.toml pyproject.toml Makefile build/. specification sandbox terraform scripts"


#Create /dist/ sub-directory and copy files into directory
#Ensure full dir structure is preserved for Lambdas
release: clean publish build-proxy
	mkdir -p dist
	for f in $(_dist_include); do cp -r $$f dist; done
	for f in $(PYTHON_PROJECT_DIRS); do cp --parents -r $$f dist; done
	cp ecs-proxies-deploy.yml dist/ecs-deploy-sandbox.yml
	cp ecs-proxies-deploy.yml dist/ecs-deploy-internal-qa-sandbox.yml
	cp ecs-proxies-deploy.yml dist/ecs-deploy-internal-dev-sandbox.yml

#################
# Test commands #
#################

TEST_CMD := @APIGEE_ACCESS_TOKEN=$(APIGEE_ACCESS_TOKEN) \
		poetry run pytest -v \
		--color=yes \
		--api-name=immunisation-fhir-api \
		--proxy-name=$(PROXY_NAME) \
		-s

PROD_TEST_CMD := $(TEST_CMD) \
		--apigee-app-id=$(APIGEE_APP_ID) \
		--status-endpoint-api-key=$(STATUS_ENDPOINT_API_KEY)

#Command to run end-to-end smoketests post-deployment to verify the environment is working
smoketest:
	$(TEST_CMD) \
	--junitxml=smoketest-report.xml \
	-m smoketest

test:
	$(TEST_CMD) \
	--junitxml=test-report.xml \

smoketest-prod:
	$(PROD_TEST_CMD) \
	--junitxml=smoketest-report.xml \
	-m smoketest

test-prod:
	$(PROD_CMD) \
	--junitxml=test-report.xml \

setup-python-envs:
	scripts/setup-python-envs.sh

initialise-all-python-venvs:
	for dir in $(PYTHON_PROJECT_DIRS); do ( \
		cd $$dir && \
		pwd && \
		rm -rf .venv && \
		python -m venv .venv && \
		source .venv/bin/activate && \
		poetry install --no-root && \
		deactivate \
	); done

update-all-python-dependencies:
	for dir in $(PYTHON_PROJECT_DIRS); do ( \
		cd $$dir && \
		pwd && \
		source .venv/bin/activate && \
		poetry update && \
		deactivate \
	); done

run-all-python-unit-tests:
	for dir in $(PYTHON_PROJECT_DIRS_WITH_UNIT_TESTS); do ( \
		cd $$dir && \
		pwd && \
		source .venv/bin/activate && \
		poetry run make test && \
		deactivate \
	); done

build-all-docker-images:
	for dir in $(PYTHON_PROJECT_DIRS_WITH_UNIT_TESTS); do \
		for dockerfile in $$(ls $$dir/*Dockerfile); do \
			echo $$dockerfile && docker build --file $$dockerfile $$dir; \
		done; \
	done
