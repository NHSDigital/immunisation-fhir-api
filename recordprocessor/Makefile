build:
	docker build -t processor-lambda-build .

package:build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build processor-lambda-build

test:
	@PYTHONPATH=src:tests python -m unittest

coverage-run:
	@PYTHONPATH=src:tests coverage run -m unittest discover

coverage-report:
	coverage report -m

coverage-html:
	coverage html

.PHONY: build package
