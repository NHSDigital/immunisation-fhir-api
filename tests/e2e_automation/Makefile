-include .env

cmd = pytest

test:
	$(cmd)

smoke-test:
	$(cmd) features/APITests -m smoke

collect-only:
	$(cmd) --collect-only
