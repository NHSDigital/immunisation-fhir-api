#!/bin/bash

DEPENDENCIES="poetry==1.8.4 moto==5.1.4 mypy-boto3-dynamodb==1.35.54 boto3==1.26.165 coverage botocore==1.29.165 jmespath==1.0.1 python-dateutil==2.9.0 urllib3==1.26.20 s3transfer==0.6.2 typing-extensions==4.12.2"
SOURCE="delta_backend"
DESC="delta"

# store current directory
current_dir=$(pwd)

# set working directory to the root of the repository
cd "$(dirname "$0")/../.."

# echo current directory
echo "Current directory: $(pwd)"

build_option=$(echo "$1" | tr '[:upper:]' '[:lower:]')

# Build the Docker image, passing dependencies as a build arg
if [ "$build_option" == "build" ]; then
  echo "Building Docker image with dependencies: $DEPENDENCIES"
  docker build -t write-logs-image -f .github/workflows/DockerFile .
else
  echo "Skip Docker image build."
fi

# Ensure logs directory exists
mkdir -p logs

# Run the unit tests in Docker, passing SOURCE and DESC as env vars
docker run --rm \
  -e DEPENDENCIES="$DEPENDENCIES" \
  -e SOURCE="$SOURCE" \
  -e DESC="$DESC" \
  -v $(pwd)/$SOURCE:/app \
  -v $(pwd)/logs:/logs \
  write-logs-image \
  sh -c 'echo "CWD: $(pwd)" > $LOGFILE && \
  ls -l /app >> $LOGFILE && \
  echo "DESC: \"$DESC\"" >> $LOGFILE && \
  echo "SOURCE: \"$SOURCE\"" >> $LOGFILE && \
  echo "DEPENDENCIES: \"$DEPENDENCIES\"" >> $LOGFILE && \
  echo "Running unit tests..." >> $LOGFILE && \
  pip install $DEPENDENCIES && \
  echo "Unit tests DONE" >> $LOGFILE '
  # python3 -m unittest discover -s $SOURCE'