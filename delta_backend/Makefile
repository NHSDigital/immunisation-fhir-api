build:
	docker build -t delta-lambda-build .

package: build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build delta-lambda-build

.PHONY: build package 
