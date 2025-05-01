FROM public.ecr.aws/lambda/python:3.10 as base

RUN pip install "poetry~=2.1.2"

COPY poetry.lock pyproject.toml README.md ./
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root --only main

# -----------------------------
FROM base as test

RUN poetry install --no-interaction --no-ansi --no-root

# Install coverage
RUN pip install coverage

COPY src src
COPY tests tests
RUN python -m unittest
RUN coverage run -m unittest discover
RUN coverage report -m
RUN coverage html

# Copy coverage report to a directory in the repo
RUN mkdir -p /output/coverage-report && cp -r htmlcov/* /output/coverage-report/

# -----------------------------
FROM base as build

COPY src .
RUN chmod 644 $(find . -type f)
RUN chmod 755 $(find . -type d)
