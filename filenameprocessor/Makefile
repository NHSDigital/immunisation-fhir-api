build:
	docker build -t imms-lambda-build -f Dockerfile .

package: build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build imms-lambda-build

test:
	poetry run python -m unittest

coverage-run:
	coverage run -m unittest discover

coverage-report:
	coverage report -m

coverage-html:
	coverage html

.PHONY: build package test coverage-run coverage-report coverage-html
