test:
	python -m unittest

init:
	terraform init
apply:
	terraform apply -auto-approve

delete-table:
	aws dynamodb delete-table --no-cli-pager --table-name imms-default-imms-events --region us-east-1 --endpoint-url http://localhost:4566 || true
gen_data:
	python generate_data.py
seed: delete-table apply gen_data
	# seed database with the latest file that was added to the sample_data directory
	python seed.py sample_data/$(shell ls -t sample_data | head -n1)

localstack:
	docker run -d --rm -it -p 4566:4566 -p 4510-4559:4510-4559 localstack/localstack:latest

.PHONY: test test-debug localstack apply init
