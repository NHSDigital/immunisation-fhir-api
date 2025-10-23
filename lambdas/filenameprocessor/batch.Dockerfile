FROM public.ecr.aws/lambda/python:3.11 as base

# Create a non-root user with a specific UID and GID
RUN mkdir -p /home/appuser && \
    echo 'appuser:x:1001:1001::/home/appuser:/sbin/nologin' >> /etc/passwd && \
    echo 'appuser:x:1001:' >> /etc/group && \
    chown -R 1001:1001 /home/appuser && pip install "poetry~=2.1.4"

# Install Poetry dependencies
# Copy filenameprocessor Poetry files
COPY ./filenameprocessor/poetry.lock ./filenameprocessor/pyproject.toml ./filenameprocessor/README.md ./

# Install filenameprocessor dependencies
WORKDIR /var/task
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root --only main

# -----------------------------
FROM base as test

# Set working directory back to Lambda task root
WORKDIR /var/task

RUN poetry install --no-interaction --no-ansi --no-root

# Install coverage
RUN pip install coverage

# Copy shared source code
COPY ./shared/src/common ./src/common

# Copy filenameprocessor source & test code
COPY ./filenameprocessor/src ./src
COPY ./filenameprocessor/tests ./tests

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

COPY ./filenameprocessor/src .
RUN chmod 644 $(find . -type f)
RUN chmod 755 $(find . -type d)
