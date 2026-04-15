# Perf tests

This project contains Locust performance tests for the Immunisation FHIR API.

To run them, ensure you have the
`APIGEE_ENVIRONMENT` : Currently, only the ref environment is supported.
`PERF_CREATE_RPS_PER_USER` : numeric

env vars set, and call `make test`.
