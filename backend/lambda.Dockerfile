FROM public.ecr.aws/lambda/python:3.11 as base

# Create a non-root user with a specific UID and GID
RUN mkdir -p /home/appuser && \
    echo 'appuser:x:1001:1001::/home/appuser:/sbin/nologin' >> /etc/passwd && \
    echo 'appuser:x:1001:' >> /etc/group && \
    chown -R 1001:1001 /home/appuser && pip install "poetry~=2.1.2"

# -----------------------------
COPY poetry.lock pyproject.toml README.md ./
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root --only main

# -----------------------------
FROM base AS test
RUN poetry install --no-interaction --no-ansi --no-root
COPY src src
COPY tests tests
ENV DYNAMODB_TABLE_NAME=example_table
RUN python -m unittest
# -----------------------------
FROM base AS build
COPY src .
RUN chmod 644 $(find . -type f) && chmod 755 $(find . -type d)
# Switch to the non-root user for running the container
USER 1001:1001
