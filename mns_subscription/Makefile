test:
	@PYTHONPATH=src:tests python -m unittest

coverage-run:
	@PYTHONPATH=src:tests coverage run -m unittest discover

coverage-report:
	coverage report -m 

coverage-html:
	coverage html
.PHONY: build package test
