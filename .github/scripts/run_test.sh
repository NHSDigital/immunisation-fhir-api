#!/bin/bash
set -e

PYTHON_VERSION="$1"
DESCRIPTION="$2"
COVERAGE_XML="sonarcloud-coverage-$3.xml"


          poetry env use 3.10
          poetry install
          poetry run coverage run -m unittest discover || echo "mesh_processor tests failed" >> ../failed_tests.txt
          poetry run coverage xml -o ../sonarcloud-mesh_processor-coverage.xml


  poetry env use "$PYTHON_VERSION"
  poetry install
  poetry run coverage run -m unittest discover || echo "$DESCRIPTION tests failed" >> ../failed_tests.txt

poetry run coverage xml -o "../$COVERAGE_XML"