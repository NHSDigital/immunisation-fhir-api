# Perf tests

This project contains Locust performance tests for the Immunisation FHIR API.

To run them, ensure you have the
`APIGEE_ENVIRONMENT` : Currently, only the ref environment is supported.
`PERF_SUPPLIER_SYSTEM` : `EMIS` or `TPP`
`PERF_CREATE_RPS_PER_USER` : numeric

env vars set, and call `make test`.

For read-only search load, use `make test-read-only` (runs the `SearchUser` Locust profile).

For MNS-with-mocked-PDS capacity work, use the `CreateUser` profile so downstream publishing and PDS lookup activity is exercised.

For direct mock-PDS rate limit testing, target the deployed mock PDS Lambda in AWS.

1. Deploy backend for the target test environment so the mock PDS Lambda exists.
2. Retrieve the mock PDS Lambda Function URL from Terraform output or AWS.
3. Export `MOCK_PDS_BASE_URL` to that Function URL.
4. Run mock rate tests:
   `make mockpdstest-average`, `make mockpdstest-boundary`, or `make mockpdstest-spike`

The rate presets are baked in:

- `make mockpdstest-average` runs at `125 rps`
- `make mockpdstest-boundary` runs at `130 rps`

Or run Locust UI against the deployed endpoint:
`MOCK_PDS_BASE_URL=https://abc123.lambda-url.eu-west-2.on.aws PERF_LOAD_PROFILE=average make mockpdstest-ui`
or
`MOCK_PDS_BASE_URL=https://abc123.lambda-url.eu-west-2.on.aws PERF_LOAD_PROFILE=spike make mockpdstest-ui`

`src/locustfile_pds_rate_limit.py` requires `MOCK_PDS_BASE_URL` and does not start a local server.

Mock PDS profile defaults are tuned for parity with earlier ref checks:

- Average profile duration default: `180s`
- Spike profile stages default: `10s warmup + 20s spike + 10s recovery`

Available load profiles:

- `make baseline`: holds traffic around the average acceptance threshold. Defaults to `125 rps` for `300s`.
- `make spike`: warms up at the average threshold, bursts above the spike threshold, then recovers. Defaults to `125 rps`, then `460 rps`, then back to `125 rps`.
- `make ramp`: increases traffic in fixed steps to identify the knee point and error envelope. Defaults to `50 rps` start, `25 rps` increments, `60s` per step, stopping after `500 rps`.

Supported environment variables:

- `MOCK_PDS_BASE_URL`: deployed mock PDS Lambda Function URL
- `PERF_LOAD_PROFILE`: `baseline`, `spike`, or `ramp`.
- `PERF_BASELINE_RPS`, `PERF_BASELINE_DURATION_SECONDS`
- `PERF_SPIKE_WARMUP_RPS`, `PERF_SPIKE_RPS`, `PERF_SPIKE_WARMUP_SECONDS`, `PERF_SPIKE_DURATION_SECONDS`, `PERF_SPIKE_RECOVERY_SECONDS`
- `PERF_RAMP_START_RPS`, `PERF_RAMP_STEP_RPS`, `PERF_RAMP_MAX_RPS`, `PERF_RAMP_STEP_DURATION_SECONDS`
  UI mode is used for perf runs in this folder.

Suggested ref runbook:

1. Run `make baseline` and confirm downstream create flow is stable at the average threshold.
2. Run `make spike` and check whether 429 responses are isolated to the burst window and whether MNS publish failures remain within expected limits.
3. Run `make ramp` to find the first step where latency, failures, or 429 volume becomes operationally unacceptable.
4. Record success rate, 429 rate, and p95/p99 latency from the generated CSV files for campaign-capacity decisions.
