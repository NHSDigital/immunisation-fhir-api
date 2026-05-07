LOCUST_FILE ?= src/locustfile.py
LOCUST ?= poetry run locust -f $(LOCUST_FILE)
MOCK_LOCUST_FILE ?= src/locustfile_pds_rate_limit.py
MOCK_LOCUST ?= poetry run locust -f $(MOCK_LOCUST_FILE)

test:
	$(LOCUST)

test-read-only:
	$(LOCUST) SearchUser

baseline:
	PERF_LOAD_PROFILE=baseline $(LOCUST) CreateUser

spike:
	PERF_LOAD_PROFILE=spike $(LOCUST) CreateUser

ramp:
	PERF_LOAD_PROFILE=ramp $(LOCUST) CreateUser

mockpds:
	$(MOCK_LOCUST) MockPdsUser

mockpdstest-average:
	PERF_LOAD_PROFILE=average PERF_MOCK_PDS_AVERAGE_RPS=125 $(MOCK_LOCUST) MockPdsUser

mockpdstest-boundary:
	PERF_LOAD_PROFILE=average PERF_MOCK_PDS_AVERAGE_RPS=130 $(MOCK_LOCUST) MockPdsUser

mockpdstest-spike:
	PERF_LOAD_PROFILE=spike $(MOCK_LOCUST) MockPdsUser

mockpdstest-ui:
	@if [ "$(PERF_LOAD_PROFILE)" != "average" ] && [ "$(PERF_LOAD_PROFILE)" != "spike" ]; then \
		echo "PERF_LOAD_PROFILE must be set to average or spike"; \
		exit 1; \
	fi
	PERF_LOAD_PROFILE=$(PERF_LOAD_PROFILE) $(MOCK_LOCUST) MockPdsUser

.PHONY: test test-read-only baseline spike ramp mockpds mockpdstest-average mockpdstest-boundary mockpdstest-spike mockpdstest-ui
