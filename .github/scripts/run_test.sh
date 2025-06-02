#!/bin/bash
set -e

PYTHON_VERSION="$1"
DESCRIPTION="$2"
COVERAGE_XML="sonarcloud-coverage-$3.xml"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment (.venv) with Poetry"
  poetry env use "$PYTHON_VERSION"

  ########### debug
  echo "Poetry environment info:"
  poetry env info || true
  ###########

  poetry install
  poetry env list
else
  echo "Using cached virtual environment (.venv)"
fi

if poetry run coverage run -m unittest discover; then
  echo "$DESCRIPTION tests passed"
else
  echo "$DESCRIPTION tests failed" >> ../failed_tests.txt
fi

poetry run coverage xml -o "../$COVERAGE_XML"