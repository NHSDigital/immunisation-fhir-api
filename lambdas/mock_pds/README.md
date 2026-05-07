# Mock PDS Lambda

This Lambda exposes a deterministic mock PDS endpoint for ref-only integration and performance testing.

It supports:

- `GET /Patient/{nhs_number}` for patient lookups used by MNS and id-sync.
- Redis-backed average and spike rate limiting with a fixed response contract.

Environment variables:

- `MOCK_PDS_AVERAGE_LIMIT`
- `MOCK_PDS_AVERAGE_WINDOW_SECONDS`
- `MOCK_PDS_SPIKE_LIMIT`
- `MOCK_PDS_SPIKE_WINDOW_SECONDS`
- `MOCK_PDS_GP_ODS_CODE`
- `REDIS_HOST`
- `REDIS_PORT`
