FROM public.ecr.aws/lambda/python:3.11 AS base

# Create non-root user
RUN mkdir -p /home/appuser && \
    echo 'appuser:x:1001:1001::/home/appuser:/sbin/nologin' >> /etc/passwd && \
    echo 'appuser:x:1001:' >> /etc/group && \
    chown -R 1001:1001 /home/appuser && pip install "poetry~=1.5.0"

# Install Poetry as root
COPY poetry.lock pyproject.toml README.md ./
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root --only main
# -----------------------------
FROM base AS test
COPY src src
COPY tests tests
RUN poetry install --no-interaction --no-ansi --no-root && \
    pytest --disable-warnings tests

# -----------------------------
FROM base AS build
COPY src .
RUN chmod 644 $(find . -type f) && chmod 755 $(find . -type d)
# Build as non-root user
USER 1001:1001
CMD ["event_processor.event_processor"]
