# immunisation-fhir-api lambda

Paths are relative to this directory, `backend`.

## Install dependencies

```shell
pip install poetry
poetry install
pip install terraform-local
```


## Run locally

### Start LocalStack

```shell
cd ../devtools
docker compose -f localstack-compose.yml up
```

LocalStack uses port 4566 so make sure it's free.


### Create table

```shell
cd ../terraform
tflocal init
tflocal apply -target=aws_dynamodb_table.test-dynamodb-table
```

### Run endpoint

Rename `.env.default` to `.env` or merge it with your existing file. 
Rename `.envrc.default` to `.envrc` or merge it with your existing file. `direnv` will use them automatically in the terminal.

These are kept separate so other tools can use `.env` if wanted.

See `.env` for an explanation of the variables.

To run from the terminal: 
```shell
cd src
python get_imms_handler.py 123
```

If not using `.envrc` then:
```shell
cd src
AWS_PROFILE=apim-dev DYNAMODB_TABLE_NAME=imms-default-imms-events IMMUNIZATION_ENV=local python get_imms_handler.py 123
```

You should get a 404 as the resource doesn't exist.


### Running tests

- `make test`
- If you want to run specific test, you can try testing one single class or single function with 
  `python -m unittest tests.test_fhir_controller.TestSearchImmunizations        `
  `python -m unittest tests.test_fhir_controller.TestSearchImmunizations.test_search_immunizations`
