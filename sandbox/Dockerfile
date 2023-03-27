FROM python:3.9-slim

ARG SERVICE_BASE_PATH

RUN pip install poetry

WORKDIR /sandbox

ADD pyproject.toml .
RUN poetry config virtualenvs.create false
RUN poetry install

COPY . /sandbox

CMD uvicorn fhir_api:app --reload --host 0.0.0.0 --port 9000 --log-level=warning
