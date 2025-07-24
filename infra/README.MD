# About 
Use .env-default as a reference for the required environment variables.
You can use the commands defined in the Makefile to interact with the infrastructure resources.

Currently, this process is run manually whenever we need to update the base layer of our infrastructure. These core resources remain consistent across all deployments.

## Running terraform
The general procedures are: 
1. Set up your environment by creating a .env file with the following values. Note: some values may require customisation based on your specific setup.
```dotenv
ENVIRONMENT=(select subfolder from environments)
AWS_PROFILE=your-profile
BUCKET_NAME=(find bucket name in aws)
TF_VAR_key=state
```
2. Run `make init` to initialize the Terraform project.
3. Run `make plan` to review the proposed infrastructure changes.
4. Once you're confident in the plan and understand its impact, execute `make apply` to apply the changes.