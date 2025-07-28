# Important 
The Mesh module is not idempotent, which is why it is kept separate from the main infrastructure folder. Each time the module is applied, it triggers the recreation of various AWS resources related to the Mesh configuration. 
There is 1 mesh mailbox for int that currently resides in the dev AWS account. This should be moved to the new INT AWS account once it becomes active.

## Running terraform
The general procedures are: 
1. Set up your environment by creating a .env file with the following values. Note: some values may require customisation based on your specific setup.
```dotenv
ENVIRONMENT=int or prod
AWS_PROFILE=your-profile
BUCKET_NAME=(find mesh bucket name in aws s3)
TF_VAR_key=state
```
2. Run `make init` to initialize the Terraform project.
3. Run `make plan` to review the proposed infrastructure changes.
4. Once you're confident in the plan and understand its impact, execute `make apply` to apply the changes.