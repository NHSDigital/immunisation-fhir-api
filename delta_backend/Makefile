build:
	docker build -t delta-lambda-build .

package: build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build delta-lambda-build

test:
	python -m unittest

.PHONY: build package 
