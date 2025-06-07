#!/bin/bash
set -e

echo "🚀 Packaging Lambda..."

# Clean previous build
rm -rf build lambda_package.zip
mkdir -p build

# Export dependencies (using poetry) and install them
poetry export -f requirements.txt --without-hashes -o requirements.txt
pip install -r requirements.txt -t build/

# Copy only the needed source code and files
cp -r src/* build/
cp pyproject.toml poetry.lock build/

# Create deployment zip
cd build
zip -r ../lambda_package.zip .
cd ..

echo "✅ Lambda package created: lambda_package.zip"
