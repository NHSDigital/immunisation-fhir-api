#!/bin/bash
set -e

echo "🚀 Packaging Lambda2..."

PROJECT="${1:-.}"
PROJECT_DIR="${2:-$(realpath \"$PROJECT\")}"  # Default to current dir if not provided
BUILD_DIR="${3:-build}"  # Default build directory if not provided
ZIP_FILE="${4:-$PROJECT.zip}"  # Default zip file name if not provided
echo "Project directory: $PROJECT_DIR"
echo "Build directory: $BUILD_DIR"
echo "Zip file: $ZIP_FILE"


# show current directory
echo "📂 Current directory: $(pwd)"


# list contents of the project directory
echo "📂 Contents of project directory:     $(ls -1 $PROJECT_DIR)"

echo "🚀 Packaging Lambda from $PROJECT_DIR..."


cd "$PROJECT_DIR"
# Ensure we are in the correct directory
echo "📂 Current directory after change: $(pwd)"

# Clean previous build
echo "🧹 Cleaning previous build..."
rm -rf "$BUILD_DIR" lambda_package.zip
echo "✅ Previous build cleaned."
echo "📂 mkdir $BUILD_DIR"
mkdir -p "$BUILD_DIR"

if [ ! -d "$BUILD_DIR" ]; then
  echo "❌ ERROR: Build directory not created!"
  exit 1
fi

echo "Exporting dependencies and packaging Lambda..."
# Export dependencies (using poetry) and install them
poetry export -f requirements.txt --without-hashes -o requirements.txt || exit 1
echo "📦 Installing dependencies to $BUILD_DIR..."
pip install -r requirements.txt -t "$BUILD_DIR" || exit 1

# Copy only the needed source code and files
echo "📂 Copying source files to $BUILD_DIR..."
cp -r src/* "$BUILD_DIR"
echo "📂 Copying additional files to $BUILD_DIR..."
# cp pyproject.toml poetry.lock "$BUILD_DIR"


# Create deployment zip
echo "📦 Creating deployment package..."
echo "📂 cd $BUILD_DIR"
cd "$BUILD_DIR"
echo "Zipping contents to ../$ZIP_FILE..."
zip -r "../$ZIP_FILE" . # -x "../$ZIP_FILE"
echo "📂 Returning to project directory... cd.."
cd ..

echo "📂 Current directory: $(pwd)"

#list contents of the build directory
echo "📂 Contents of build directory:     $(ls -1 $BUILD_DIR/$ZIP_FILE)"

echo "📂 Contents of parent directory:     $(ls -1 $PROJECT_DIR/$ZIP_FILE)"

# lis contents of the zip file
echo "📦 Contents of the zip file: $(unzip -l $ZIP_FILE | tail -n +4 | head -n -2)"

echo "✅ Lambda package created: $ZIP_FILE"
