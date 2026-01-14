-include .env

cmd = poetry run pytest

test:
	$(cmd)

test-api-smoke:
	$(cmd) features/APITests -m smoke

test-api-full:
	$(cmd) features/APITests -m functional

test-batch-smoke:
	$(cmd) features/batchTests -m smoke

test-batch-full:
	$(cmd) features/batchTests -m functional

collect-only:
	$(cmd) --collect-only
