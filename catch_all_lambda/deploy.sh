

# Create a dist folder the Lambda and copy only the js files and node_modules
# AWS Lambda does not have a use for a package.json or typescript files at runtime.

# Lambda 1
mkdir -p dist/catch-all && \
cp -r ./src/catch-all.py dist/catch-all/ 
cd dist/catch-all && \
rm -f catch-all.zip && \
zip -r catch-all.zip . && \
mv catch-all.zip ../../../terraform/zips/ && \
cd ../..
rm -rf dist


# Zip Lambda's code and move to the terraform directory

# Lambda 1
# cd dist/catch-all && \
# rm -f catch-all.zip && \
# zip -r catch-all.zip . && \
# mv catch-all.zip ../../terraform/zips/ && \
# cd ../..

# Delete the dist folder for cleanup
# rm -rf dist