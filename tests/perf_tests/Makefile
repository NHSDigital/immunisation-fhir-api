TEST_ENV := @PYTHONPATH=src:tests:../../lambdas/shared/src:../../lambdas/shared/tests

test:
	$(TEST_ENV) poetry run locust -f src/locustfile.py

.PHONY: test
