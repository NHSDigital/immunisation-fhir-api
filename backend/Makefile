build:
	docker build -t imms-lambda-build -f lambda.Dockerfile .

package: build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build imms-lambda-build

test:
	@PYTHONPATH=src:tests python -m unittest

.PHONY: build package test
