    
    
# Run the npm commands to transpile the TypeScript to JavaScript
npm i && \
npm run build && \
npm prune --production

# Create a dist folder the Lambda and copy only the js files and node_modules
# AWS Lambda does not have a use for a package.json or typescript files at runtime.

# Lambda 1
mkdir -p dist/index && \
cp -r ./src/index.js dist/index/ && \
cp -r ./node_modules dist/index/

# Zip Lambda's code and move to the terraform directory

# Lambda 1
cd dist/index && \
rm -f lambda_function.zip && \
zip -r lambda_function.zip . && \
mv lambda_function.zip ../../terraform/zips/ && \
cd ../..

# Delete the dist folder for cleanup
rm -rf dist