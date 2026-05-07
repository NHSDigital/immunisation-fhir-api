FROM public.ecr.aws/lambda/python:3.11 AS base

ENV PIP_ONLY_BINARY=:all: \
    POETRY_INSTALLER_ONLY_BINARY=:all:

RUN mkdir -p /home/appuser && \
    echo 'appuser:x:1001:1001::/home/appuser:/sbin/nologin' >> /etc/passwd && \
    echo 'appuser:x:1001:' >> /etc/group && \
    chown -R 1001:1001 /home/appuser && \
        printf '%s %s\n' \
            'poetry==2.1.4' \
            '--hash=sha256:0019b64d33fed9184a332f7fad60ca47aace4d6a0e9c635cdea21b76e96f32ce' \
            > /tmp/poetry-requirements.txt && \
    pip install --only-binary :all: --require-hashes -r /tmp/poetry-requirements.txt && \
    rm -f /tmp/poetry-requirements.txt

COPY ./mock_pds/poetry.lock ./mock_pds/pyproject.toml ./

WORKDIR /var/task
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root --only main

FROM base AS build

WORKDIR /var/task

COPY ./mock_pds/src .

RUN chmod 644 $(find . -type f) && chmod 755 $(find . -type d)

USER 1001:1001

CMD ["lambda_handler.lambda_handler"]