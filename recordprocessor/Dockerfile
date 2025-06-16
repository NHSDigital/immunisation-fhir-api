FROM public.ecr.aws/lambda/python:3.10 AS base

# Create a non-root user with a specific UID and GID
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
# @TODO include following lines to include shared code
# COPY common_src common_src
# ENV PYTHONPATH=/var/task/common_src:/var/task/src:$PYTHONPATH
COPY tests tests
RUN poetry install --no-interaction --no-ansi --no-root && \
    pytest --disable-warnings tests

# -----------------------------
FROM base AS build

COPY src .
RUN chmod 644 $(find . -type f) && chmod 755 $(find . -type d)
# Switch to the non-root user for running the container
USER 1001:1001
CMD ["python", "batch_processing.py"]
ENTRYPOINT ["python", "batch_processing.py"]
