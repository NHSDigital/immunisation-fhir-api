#!/bin/bash
set -e

echo "🚀 Packaging Lambda1..."

PROJECT_DIR="${1:-.}"  # Default to current dir if not provided

# show current directory
echo "📂 Current directory: $(pwd)
Project directory: $PROJECT_DIR"
# list contents of the project directory
echo "📂 Contents of project directory:     $(ls -1 $PROJECT_DIR)"

echo "🚀 Packaging Lambda from $PROJECT_DIR..."


cd "$PROJECT_DIR"
# Ensure we are in the correct directory
echo "📂 Current directory after change: $(pwd)"

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
