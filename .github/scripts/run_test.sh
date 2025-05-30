#!/bin/bash
set -e

PYTHON_VERSION="$1"
DESCRIPTION="$2"
COVERAGE_XML="sonarcloud-coverage-$3.xml"

echo "Using Python $PYTHON_VERSION"
poetry env use "$PYTHON_VERSION"
poetry config virtualenvs.in-project true
poetry install

if poetry run coverage run -m unittest discover; then
  echo "$DESCRIPTION tests passed"
else
  echo "$DESCRIPTION tests failed" >> ../failed_tests.txt
fi

poetry run coverage xml -o "../$COVERAGE_XML"
# poetry env list --full-path | awk '{print $1}' | xargs -n 1 poetry env remove || true
