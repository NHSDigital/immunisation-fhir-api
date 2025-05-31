#!/bin/bash
set -e

PYTHON_VERSION="$1"
DESCRIPTION="$2"
COVERAGE_XML="sonarcloud-coverage-$3.xml"

echo "Using Python $PYTHON_VERSION"
poetry config virtualenvs.in-project true

# Only create/use the env and install if .venv does not exist
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment (.venv) with Poetry"
  poetry env use "$PYTHON_VERSION"
  poetry install
else
  echo "Using cached virtual environment (.venv)"
fi

if poetry run coverage run -m unittest discover; then
  echo "$DESCRIPTION tests passed"
else
  echo "$DESCRIPTION tests failed" >> ../failed_tests.txt
fi

poetry run coverage xml -o "../$COVERAGE_XML"