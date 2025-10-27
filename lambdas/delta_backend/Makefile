TEST_ENV := @PYTHONPATH=src:tests:../shared/src

build:
	docker build -t delta-lambda-build .

package: build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build delta-lambda-build

test:
	$(TEST_ENV) python -m unittest

check-conversion:
	$(TEST_ENV) python tests/check_conversion.py

coverage-run:
	$(TEST_ENV) coverage run -m unittest discover -v

coverage-report:
	$(TEST_ENV) coverage report -m 

coverage-html:
	$(TEST_ENV) coverage html  

.PHONY: build package 
