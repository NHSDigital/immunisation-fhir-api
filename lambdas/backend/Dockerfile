FROM public.ecr.aws/lambda/python:3.11 AS base

RUN mkdir -p /home/appuser && \
    echo 'appuser:x:1001:1001::/home/appuser:/sbin/nologin' >> /etc/passwd && \
    echo 'appuser:x:1001:' >> /etc/group && \
    chown -R 1001:1001 /home/appuser && pip install "poetry~=2.1.4"

# Install Poetry dependencies
# Copy backend Poetry files
COPY ./backend/poetry.lock ./backend/pyproject.toml ./

# Install backend dependencies
WORKDIR /var/task
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root --only main

# -----------------------------
FROM base AS build

# Set working directory back to Lambda task root
WORKDIR /var/task

# Copy shared source code
COPY ./shared/src/common ./common

# Copy backend source code
COPY ./backend/src .

# Set correct permissions
RUN chmod 644 $(find . -type f) && chmod 755 $(find . -type d)

# Switch to the non-root user for running the container
USER 1001:1001

