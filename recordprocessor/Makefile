build:
	docker build -t processor-lambda-build .

package:build
	mkdir -p build
	docker run --rm -v $(shell pwd)/build:/build processor-lambda-build
test:
	# TODO for shared code PYTHONPATH=src:../common/src python -m unittest	
	python -m unittest	

coverage run:
	# TODO for shared code PYTHONPATH=src:../common/src coverage run -m unittest discover
	coverage run -m unittest discover

coverage report:
	coverage report -m 

coverage html:
	coverage html  

.PHONY: build package