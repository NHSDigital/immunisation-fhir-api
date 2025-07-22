test:
	@PYTHONPATH=src:../ python -m unittest discover -s tests -p "test_*.py" -v

test-list:
	@PYTHONPATH=src:tests python -m unittest discover -s tests -p "test_*.py" --verbose | grep test_

coverage-run:
	@PYTHONPATH=src coverage run --source=src -m unittest discover -s tests -p "test_*.py" -v

coverage-report:
	@PYTHONPATH=src coverage report -m

coverage-html:
	@PYTHONPATH=src coverage html

coverage: coverage-run coverage-report

coverage-full: coverage-run coverage-report coverage-html

.PHONY: build package test test-list coverage-run coverage-report coverage-html coverage coverage-full
