# About 
Use .env-default as a reference for the required environment variables.
You can use the commands defined in the Makefile to interact with the infrastructure resources.

Currently, this process is run manually whenever we need to update the base layer of our infrastructure. These core resources remain consistent across all deployments.

## Steps
The general procedures are: 
1. Configure your environment by copying and updating `.env` based on the `.env-default` file.
2. Run `make init` to initialize the Terraform project.
3. Run `make plan` to review the proposed infrastructure changes.

4. Once you're confident in the plan and understand its impact, execute `make apply` to apply the changes.