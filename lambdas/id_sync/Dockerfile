FROM public.ecr.aws/lambda/python:3.11 AS base

# Create non-root user
RUN mkdir -p /home/appuser && \
    echo 'appuser:x:1001:1001::/home/appuser:/sbin/nologin' >> /etc/passwd && \
    echo 'appuser:x:1001:' >> /etc/group && \
    chown -R 1001:1001 /home/appuser && pip install "poetry~=1.5.0"

# Install Poetry dependencies
# Copy id_sync Poetry files
COPY ./id_sync/poetry.lock ./id_sync/pyproject.toml ./
COPY ./shared/src/common ./src/common

RUN echo "Listing /var/task after source code copy:" && ls -R /var/task

# Install id_sync dependencies
WORKDIR /var/task
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root --only main

# -----------------------------
FROM base AS build

# Set working directory back to Lambda task root
WORKDIR /var/task

# Copy shared source code
COPY ./shared/src/common ./common

# Copy id_sync source code
COPY ./id_sync/src .

# Set correct permissions
RUN chmod 644 $(find . -type f) && chmod 755 $(find . -type d)

# Build as non-root user
USER 1001:1001

# Set the Lambda handler
CMD ["id_sync.handler"]
