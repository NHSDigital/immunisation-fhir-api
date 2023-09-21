# immunisation-fhir-api
This is lambdas for the *immunisation-fhir-api* API.

## Set up your TypeScript Lambda function:
Make sure you have your TypeScript Lambda function code structured properly in a directory. For example, you might have a directory structure like this:
lambda/
├── src/
│   └── index.ts
├── package.json
└── tsconfig.json

## Install npm dependencies (if any):

If your TypeScript Lambda function has npm dependencies, make sure they are installed in the project directory. You can do this by running:
`npm install`

### Build your TypeScript code:
Before creating a ZIP file, you need to build your TypeScript code into JavaScript. Navigate to the directory where your tsconfig.json file is located and run:
`tsc`
This command will compile your TypeScript code into JavaScript and place the output files in the specified directory.

In the package.json, added this build command in the scripts: 
` "build": "tsc" `


### Create a ZIP file:
To create a ZIP file containing your Lambda function code, navigate to the directory where your TypeScript code and built JavaScript files are located. Then, create a ZIP archive that includes your Lambda function code and its dependencies (if any) using the zip command. 

### Specify the ZIP file in your Terraform configuration:
In your Terraform configuration for the Lambda function, you can specify the location of the ZIP file using the filename argument in the aws_lambda_function resource block. 
