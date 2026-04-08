USERS      ?= 250
SPAWN_RATE ?= 50
RUN_TIME   ?= 5m

# Interactive UI — single process, useful for smoke tests
test:
	poetry run locust -f src/locustfile.py

# Interactive UI — search only
test-read-only:
	poetry run locust -f src/locustfile.py SearchUser

# Headless distributed — master + N workers, runs for 5 minutes then exits
test-headless:
	poetry run locust -f src/locustfile.py \
		--headless \
		--users $(USERS) \
		--spawn-rate $(SPAWN_RATE) \
		--run-time $(RUN_TIME)

# Search-only headless distributed
test-read-only-headless:
	poetry run locust -f src/locustfile.py SearchUser \
	  --headless \
	  --users $(USERS) \
	  --spawn-rate $(SPAWN_RATE) \
	  --run-time $(RUN_TIME)

.PHONY: test test-read-only test-headless test-read-only-headless