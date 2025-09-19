TEST_ENV := @PYTHONPATH=src:tests:../shared/src

test:
	$(TEST_ENV) python -m unittest

coverage-run:
	$(TEST_ENV) coverage run -m unittest discover -v

coverage-report:
	$(TEST_ENV) coverage report -m

coverage-html:
	$(TEST_ENV) coverage html


.PHONY: build package