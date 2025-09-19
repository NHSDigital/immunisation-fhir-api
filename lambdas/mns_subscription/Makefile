RUN_ENV := @PYTHONPATH=src:../shared/src

subscribe:
	$(RUN_ENV) poetry run python src/subscribe_mns.py

unsubscribe:
	$(RUN_ENV) poetry run python src/unsubscribe_mns.py

TEST_ENV := @PYTHONPATH=src:tests:../shared/src

test:
	$(TEST_ENV) python -m unittest

coverage-run:
	$(TEST_ENV) coverage run -m unittest discover

coverage-report:
	$(TEST_ENV) coverage report -m 

coverage-html:
	$(TEST_ENV) coverage html

.PHONY: build package test
