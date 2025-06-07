#!/bin/bash
set -e

PROJECT_DIR="${1:-.}"  # Default to current dir if not provided

echo "🚀 Packaging Lambda from $PROJECT_DIR..."

# Clean previous build
rm -rf build lambda_package.zip
mkdir -p build

# Export dependencies (using poetry) and install them
poetry export -f requirements.txt --without-hashes -o requirements.txt
pip install -r requirements.txt -t build/

# Copy only the needed source code and files
cp -r "$PROJECT_DIR"/* build/
cp "$PROJECT_DIR"/pyproject.toml "$PROJECT_DIR"/poetry.lock build/

# Create deployment zip
cd build
zip -r ../lambda_package.zip .
cd ..

echo "✅ Lambda package created: lambda_package.zip"
