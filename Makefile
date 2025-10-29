SHELL=/usr/bin/env bash -euo pipefail

PYTHON_PROJECT_DIRS_WITH_UNIT_TESTS = backend batch_processor_filter lambdas/ack_backend lambdas/delta_backend lambdas/filenameprocessor lambdas/id_sync lambdas/mesh_processor lambdas/mns_subscription lambdas/recordprocessor lambdas/redis_sync lambdas/shared
PYTHON_PROJECT_DIRS = tests/e2e tests/e2e_batch quality_checks $(PYTHON_PROJECT_DIRS_WITH_UNIT_TESTS)

.PHONY: install lint format format-check clean publish build-proxy release initialise-all-python-venvs update-all-python-dependencies run-all-python-unit-tests build-all-docker-images

#Installs dependencies using npm.
install:
	npm install --legacy-peer-deps

#Run the npm linting script (specified in package.json). Used to check the syntax and formatting of files.
lint:
	npm run lint

format:
	npm run format

format-check:
	npm run format-check

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
	utilities/scripts/build_proxy.sh

#Files to loop over in release
_dist_include="poetry.toml Makefile build/. specification sandbox utilities/scripts"

#Create /dist/ sub-directory and copy files into directory
#Ensure full dir structure is preserved for Lambdas
release: clean publish build-proxy
	mkdir -p dist
	for f in $(_dist_include); do cp -r $$f dist; done
	cp ecs-proxies-deploy.yml dist/ecs-deploy-sandbox.yml
	cp ecs-proxies-deploy.yml dist/ecs-deploy-internal-qa-sandbox.yml
	cp ecs-proxies-deploy.yml dist/ecs-deploy-internal-dev-sandbox.yml

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
