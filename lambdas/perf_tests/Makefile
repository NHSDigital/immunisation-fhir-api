TEST_ENV := @PYTHONPATH=src:tests:../shared/src:../shared/tests

test:
	$(TEST_ENV) poetry run locust -f src/locustfile.py

.PHONY: test
