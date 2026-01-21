-include .env

environment         ?= $(ENVIRONMENT)
region              ?= $(AWS_REGION)

tf_cmd = AWS_PROFILE=$(AWS_PROFILE) terraform

bucket_name = immunisation-grafana-terraform-state
#bucket_name = immunisation-$(environment)-grafana-terraform-state
state_key=state/$(environment)/terraform.tfstate

tf_state = \
  -backend-config="key=$(state_key)" \
  -backend-config="bucket=$(bucket_name)" \
  -backend-config="region=$(region)" 

tf_vars = \
  -var="environment=$(environment)" \
  -var-file="./terraform.tfvars"

tf_bucket_vars = \
  --bucket "$(bucket_name)" \
  --region "$(region)" \
  --create-bucket-configuration LocationConstraint="$(region)"

tf_bucket_versioning = \
  --versioning-configuration Status=Enabled \

bucket-exists:
	@echo 'Checking if the S3 bucket $(bucket_name) exists...'
	@aws s3 ls $(bucket_name) >/dev/null 2>&1 || echo "aws s3 bucket $(bucket_name) does not exist"

bucket-create:
	aws s3api create-bucket $(tf_bucket_vars)
	aws s3api put-bucket-versioning $(tf_bucket_versioning)

init:
	$(tf_cmd) init $(tf_state) -upgrade

init-reconfigure:
	$(tf_cmd) init $(tf_state) -reconfigure

workspace:
	$(tf_cmd) workspace select -or-create $(environment) && echo "Switched to workspace/environment: $(environment)"

plan: workspace
	 $(tf_cmd) plan $(tf_vars)

plan-ci: workspace
	 $(tf_cmd) plan $(tf_vars) -out=tfplan -input=false

plan-changes: workspace
	 $(tf_cmd) plan $(tf_vars) -out=plan && $(tf_cmd) show -no-color -json plan | jq -r '.resource_changes[] | select(.change.actions[0]=="update" or .change.actions[0]=="create" or .change.actions[0]=="add") | .address'

# TODO: don't implement 'apply' - the actual application will be in infrastructure/account

clean:
	rm -rf build .terraform upload-key

.PHONY : workspace init plan clean
