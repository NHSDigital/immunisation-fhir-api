FROM public.ecr.aws/lambda/python:3.9


RUN pip install poetry

WORKDIR /project

ADD pyproject.toml .
RUN poetry config virtualenvs.create false
RUN poetry install

ADD fhir_api ./fhir_api

CMD ["fhir_api.app.handler"]
