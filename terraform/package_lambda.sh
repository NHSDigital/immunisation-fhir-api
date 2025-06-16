#!/bin/bash
set -e
echo "🚀 Packaging Lambda..."

PROJECT="${1:-.}"
PROJECT_DIR="${2:-$(realpath "$PROJECT")}"  # Default to current dir if not provided
BUILD_DIR="${3:-build}"  # Default build directory if not provided
ZIP_FILE="${4:-$(basename "$PROJECT_DIR").zip}"  # Default zip file name if not provided

echo "Project directory: $PROJECT_DIR"
echo "Build directory: $BUILD_DIR"
echo "Zip filename: $ZIP_FILE"

cd "$PROJECT_DIR"
# Clean previous build
echo "🧹 Cleaning previous build..."
rm -rf "$BUILD_DIR" "$ZIP_FILE"
echo "✅ Previous build cleaned."
echo "📂 mkdir $BUILD_DIR"
mkdir -p "$BUILD_DIR"

if [ ! -d "$BUILD_DIR" ]; then
  echo "❌ ERROR: Build directory not created!"
  exit 1
fi

pyenv install -s 3.11.12
pyenv global 3.11.12
python --version

# Check for poetry and python3.11
command -v poetry >/dev/null 2>&1 || { echo "❌ poetry not found. Please install poetry."; exit 1; }
command -v python3.11 >/dev/null 2>&1 || { echo "❌ python3.11 not found. Please install Python 3.11."; exit 1; }

poetry lock
if [ $? -ne 0 ]; then
  echo "❌ ERROR: Poetry lock failed. Check your poetry configuration."
  exit 1
fi
echo "Exporting dependencies and packaging Lambda..."
poetry export -f requirements.txt --without-hashes -o requirements.txt || exit 1

echo "📦 Installing dependencies to $BUILD_DIR..."
python3.11 -m pip install -r requirements.txt -t "$BUILD_DIR" || exit 1

# Copy only the needed source code and files
echo "📂 Copying source files to $BUILD_DIR..."
cp -r src/* "$BUILD_DIR"

# Create deployment zip
echo "📦 Creating deployment package..."
cd "$BUILD_DIR"
zip -r "../$ZIP_FILE" . -x "../$ZIP_FILE"

echo "✅ Lambda package created: $ZIP_FILE"