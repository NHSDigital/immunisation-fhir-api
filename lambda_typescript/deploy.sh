    
    
  # Run the npm commands to transpile the TypeScript to JavaScript
  npm i && \
  npm run build && \
  npm prune --production &&\
  # Create a dist folder and copy only the js files to distribution.
  # AWS Lambda does not have a use for a package.json or typescript files on runtime.
  mkdir dist &&\
  cp -r ./src/*.js dist/ &&\
  cp -r ./node_modules dist/ &&\
  cd dist &&\
  find . -name "*.zip" -type f -delete && \
  #Create zips directory under terraform, delete existing one
  rm -rf ../../terraform/zips
  mkdir ../../terraform/zips
  # Zip everything in the dist folder and move to terraform directory
  zip -r ../../terraform/zips/lambda_function.zip . && \
  #Delete Distibution folder
  cd .. && rm -rf dist