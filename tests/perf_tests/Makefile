LOCUST_FILE ?= src/locustfile.py
LOCUST ?= poetry run locust -f $(LOCUST_FILE)
RESULTS_DIR ?= results
RESULTS_PREFIX ?= $(RESULTS_DIR)/$(PERF_LOAD_PROFILE)

test:
	$(LOCUST)

test-read-only:
	$(LOCUST) SearchUser

baseline:
	mkdir -p $(RESULTS_DIR)
	PERF_LOAD_PROFILE=baseline $(LOCUST) CreateUser --headless --only-summary --csv $(RESULTS_PREFIX)

spike:
	mkdir -p $(RESULTS_DIR)
	PERF_LOAD_PROFILE=spike $(LOCUST) CreateUser --headless --only-summary --csv $(RESULTS_PREFIX)

ramp:
	mkdir -p $(RESULTS_DIR)
	PERF_LOAD_PROFILE=ramp $(LOCUST) CreateUser --headless --only-summary --csv $(RESULTS_PREFIX)

.PHONY: test test-read-only baseline spike ramp
