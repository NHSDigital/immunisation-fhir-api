
test:
	@PYTHONPATH=src:tests:../shared/src python -m unittest

coverage-run:
	coverage run -m unittest discover -v

coverage-report:
	coverage report -m

coverage-html:
	coverage html

.PHONY: build package