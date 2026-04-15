TEST_ENV := @PYTHONPATH=src:tests:../shared/src

build:
	docker build -t processor-lambda-build .

package:build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build processor-lambda-build

test:
	$(TEST_ENV) python -m unittest

coverage-run:
	$(TEST_ENV) coverage run --source=src -m unittest discover

coverage-report:
	$(TEST_ENV) coverage report -m

coverage-html:
	$(TEST_ENV) coverage html

.PHONY: build package
