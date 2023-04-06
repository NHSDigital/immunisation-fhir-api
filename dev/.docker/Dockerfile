FROM python:3.9-slim

RUN pip install poetry

WORKDIR /project

ADD pyproject.toml .
RUN poetry config virtualenvs.create false
RUN poetry install

ADD fhir_api ./fhir_api

CMD uvicorn fhir_api:app --reload --host $SERVER_HOST --port $SERVER_PORT --log-level=warning
