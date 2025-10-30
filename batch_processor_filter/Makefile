build:
	docker build -t imms-lambda-build -f Dockerfile .

package: build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build imms-lambda-build

test:
	@PYTHONPATH=src:tests python -m unittest

coverage-run:
	@PYTHONPATH=src:tests coverage run --source=src -m unittest discover

coverage-report:
	coverage report -m

coverage-html:
	coverage html

.PHONY: build package test
