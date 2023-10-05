    
    
# Run the npm commands to transpile the TypeScript to JavaScript
npm i && \
npm run build && \
npm prune --production

# Create a dist folder for each Lambda and copy only the js files and node_modules
# AWS Lambda does not have a use for a package.json or typescript files at runtime.

# Lambda 1
mkdir -p dist/index && \
cp -r ./src/index.js dist/index/ && \
cp -r ./node_modules dist/index/

# Lambda 2
mkdir -p dist/catch-all && \
cp -r ./src/catch-all.js dist/catch-all/ && \
cp -r ./node_modules dist/catch-all/

# Zip each Lambda's code and move to the terraform directory

# Lambda 1
cd dist/index && \
rm -f lambda_function.zip && \
zip -r lambda_function.zip . && \
mv lambda_function.zip ../../terraform/zips/ && \
cd ../..

# Lambda 2
cd dist/catch-all && \
rm -f catch-all.zip && \
zip -r catch-all.zip . && \
mv catch-all.zip ../../terraform/zips/ && \
cd ..

# Delete the dist folder for cleanup
rm -rf dist