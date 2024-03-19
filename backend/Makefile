build:
	docker build -t imms-lambda-build -t lambda.Dockerfile .

package: build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build imms-lambda-build

test:
	python -m unittest

.PHONY: build package test
