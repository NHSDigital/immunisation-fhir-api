test:
	poetry run locust -f src/locustfile.py

test-read-only:
	poetry run locust -f src/locustfile.py SearchUser

.PHONY: test test-read-only
