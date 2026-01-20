-include .env

cmd = poetry run pytest
# Add sandbox, add to README
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

test-sandbox:
	$(cmd) features -m sandbox

collect-only:
	$(cmd) --collect-only
