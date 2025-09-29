FROM public.ecr.aws/lambda/python:3.11 AS base

# Create non-root user
RUN mkdir -p /home/appuser && \
    echo 'appuser:x:1001:1001::/home/appuser:/sbin/nologin' >> /etc/passwd && \
    echo 'appuser:x:1001:' >> /etc/group && \
    chown -R 1001:1001 /home/appuser && pip install "poetry~=2.1.4"

# Install redis_sync dependencies
WORKDIR /var/task
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root --only main

# Install Poetry dependencies
# Copy redis_sync Poetry files
COPY ./redis_sync/poetry.lock ./redis_sync/pyproject.toml ./

# -----------------------------
FROM base AS build

# Set working directory back to Lambda task root
WORKDIR /var/task

# Copy shared source code
COPY ./shared/src/common ./common

# Copy redis_sync source code
COPY ./redis_sync/src .

# Set correct permissions
RUN chmod 644 $(find . -type f) && chmod 755 $(find . -type d)

# Build as non-root user
USER 1001:1001

# Set the Lambda handler
CMD ["redis_sync.handler"]
