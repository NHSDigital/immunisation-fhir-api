build:
	docker build -t delta-lambda-build .

package: build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build delta-lambda-build

test:
	python -m unittest

check-conversion:
	python tests/check_conversion.py

coverage-run:
	coverage run -m unittest discover -v

coverage-report:
	coverage report -m 

coverage-html:
	coverage html  

.PHONY: build package 
