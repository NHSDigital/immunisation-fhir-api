#!/bin/bash
set -e

echo "🚀 Packaging Lambda1..."

PROJECT_DIR="${1:-.}"  # Default to current dir if not provided
BUILD_DIR="${2:-build}"  # Default build directory if not provided
echo "Project directory: $PROJECT_DIR"
echo "Build directory: $BUILD_DIR"

# show current directory
echo "📂 Current directory: $(pwd)

# list contents of the project directory
echo "📂 Contents of project directory:     $(ls -1 $PROJECT_DIR)"

echo "🚀 Packaging Lambda from $PROJECT_DIR..."


cd "$PROJECT_DIR"
# Ensure we are in the correct directory
echo "📂 Current directory after change: $(pwd)"

# Clean previous build
rm -rf "$BUILD_DIR" lambda_package.zip
mkdir -p "$BUILD_DIR"

# Export dependencies (using poetry) and install them
poetry export -f requirements.txt --without-hashes -o requirements.txt
pip install -r requirements.txt -t "$BUILD_DIR"

# Copy only the needed source code and files
cp -r src/* "$BUILD_DIR"
cp pyproject.toml poetry.lock "$BUILD_DIR"

# Create deployment zip
cd "$BUILD_DIR"
zip -r ../lambda_package.zip .
cd ..

echo "✅ Lambda package created: lambda_package.zip"
