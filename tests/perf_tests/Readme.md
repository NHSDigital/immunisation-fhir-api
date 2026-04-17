# Perf tests

This project contains Locust performance tests for the Immunisation FHIR API.

To run them, ensure you have the
`APIGEE_ENVIRONMENT` : Currently, only the ref environment is supported.
`PERF_SUPPLIER_SYSTEM` : `EMIS` or `TPP`
`PERF_CREATE_RPS_PER_USER` : numeric

env vars set, and call `make test`.

For MNS-with-mocked-PDS capacity work, use the `CreateUser` profile so downstream publishing and PDS lookup activity is exercised.

Available load profiles:

- `make baseline`: holds traffic around the average acceptance threshold. Defaults to `125 rps` for `300s`.
- `make spike`: warms up at the average threshold, bursts above the spike threshold, then recovers. Defaults to `125 rps`, then `460 rps`, then back to `125 rps`.
- `make ramp`: increases traffic in fixed steps to identify the knee point and error envelope. Defaults to `50 rps` start, `25 rps` increments, `60s` per step, stopping after `500 rps`.

Supported environment variables:

- `PERF_LOAD_PROFILE`: `baseline`, `spike`, or `ramp`.
- `PERF_BASELINE_RPS`, `PERF_BASELINE_DURATION_SECONDS`
- `PERF_SPIKE_WARMUP_RPS`, `PERF_SPIKE_RPS`, `PERF_SPIKE_WARMUP_SECONDS`, `PERF_SPIKE_DURATION_SECONDS`, `PERF_SPIKE_RECOVERY_SECONDS`
- `PERF_RAMP_START_RPS`, `PERF_RAMP_STEP_RPS`, `PERF_RAMP_MAX_RPS`, `PERF_RAMP_STEP_DURATION_SECONDS`
- `RESULTS_DIR`: output directory for Locust CSV summaries.

Each headless profile writes Locust CSV output to `results/<profile>*`. Review:

- request counts and failures to quantify the percentage of 429 responses
- `*_stats.csv` for p50/p95/p99 latency
- `*_failures.csv` for error mix and throttle onset timing

Suggested ref runbook:

1. Run `make baseline` and confirm downstream create flow is stable at the average threshold.
2. Run `make spike` and check whether 429 responses are isolated to the burst window and whether MNS publish failures remain within expected limits.
3. Run `make ramp` to find the first step where latency, failures, or 429 volume becomes operationally unacceptable.
4. Record success rate, 429 rate, and p95/p99 latency from the generated CSV files for campaign-capacity decisions.
