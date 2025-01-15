build:
	docker build -t ack-lambda-build .

package: build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build ack-lambda-build
	
test:
	python -m unittest

.PHONY: build package 
