build:
	docker build -t mesh-lambda-build .

package: build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build mesh-lambda-build

test:
	python -m unittest

.PHONY: build package test
