#!/usr/bin/env bash

set -Eeuo pipefail
PYTHON_VERSION_REGEX='3\..+$'

pyenv install -s "$(grep -Eo $PYTHON_VERSION_REGEX .envrc)"

eval "$(direnv export bash)"
direnv allow

cd lambda_code

pyenv install -s "$(grep -Eo $PYTHON_VERSION_REGEX .envrc)"

eval "$(direnv export bash)"
direnv allow


