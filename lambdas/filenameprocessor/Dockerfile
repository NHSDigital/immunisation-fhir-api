FROM public.ecr.aws/lambda/python:3.13 AS base

# Create non-root user
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
FROM base AS build

# Set working directory back to Lambda task root
WORKDIR /var/task

# Copy shared source code
COPY ./shared/src/common ./common

# Copy filenameprocessor source code
COPY ./filenameprocessor/src .

# Set correct permissions
RUN chmod 644 $(find . -type f) && chmod 755 $(find . -type d)

# Switch to the non-root user for running the container
USER 1001:1001

# Set the Lambda handler
CMD ["file_name_processor.lambda_handler"]
