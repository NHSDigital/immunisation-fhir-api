
test:
	@PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" -v

test-list:
	@PYTHONPATH=src:tests:tests python -m unittest discover -s tests/common -p "test_*.py" --verbose | grep test_

coverage-run:
	@PYTHONPATH=src:tests coverage run -m unittest discover -v

coverage-report:
	coverage report -m

coverage-html:
	coverage html

.PHONY: build package test