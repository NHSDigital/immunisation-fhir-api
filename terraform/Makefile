-include .env

apigee_environment ?= $(APIGEE_ENVIRONMENT)
environment        ?= $(ENVIRONMENT)
sub_environment    ?= $(SUB_ENVIRONMENT)
sub_environment_dir := $(if $(findstring pr-,$(sub_environment)),pr,$(sub_environment))

tf_cmd = AWS_PROFILE=$(AWS_PROFILE) terraform

bucket_name = $(if $(filter dev,$(environment)),immunisation-$(apigee_environment),immunisation-$(environment))-terraform-state-files

tf_state = -backend-config="bucket=$(bucket_name)"

tf_vars = \
  -var="sub_environment=$(sub_environment)" \
  -var-file="./environments/$(environment)/$(sub_environment_dir)/variables.tfvars"

lock-provider:
	# Run this only when you install a new terraform provider. This will generate sha code in lock file for all platform
	echo "This may take a while. Be patient!"
	$(tf_cmd) providers lock -platform=darwin_arm64 -platform=darwin_amd64 -platform=linux_amd64 -platform=windows_amd64

workspace:
	$(tf_cmd) workspace select -or-create $(sub_environment) && echo "Switched to workspace/environment: $(sub_environment)"

init:
	$(tf_cmd) init $(tf_state) -upgrade  $(tf_vars)

init-reconfigure:
	$(tf_cmd) init $(tf_state) -upgrade $(tf_vars) -reconfigure

plan: workspace
	 $(tf_cmd) plan $(tf_vars)

plan-ci: workspace
	 $(tf_cmd) plan $(tf_vars) -out=tfplan -input=false

plan-changes: workspace
	 $(tf_cmd) plan $(tf_vars) -out=plan && $(tf_cmd) show -no-color -json plan | jq -r '.resource_changes[] | select(.change.actions[0]=="update" or .change.actions[0]=="create" or .change.actions[0]=="add") | .address'

# TODO - remove --auto-approve once we've switched to the new deployment pipeline in GitHub Actions
apply: workspace
	$(tf_cmd) apply $(tf_vars) --auto-approve

apply-ci: workspace
	$(tf_cmd) apply $(tf_vars) -input=false tfplan

clean:
	rm -rf build .terraform upload-key

destroy: workspace
	$(tf_cmd) destroy $(tf_vars) -auto-approve
	$(tf_cmd) workspace select default
	$(tf_cmd) workspace delete $(sub_environment)

output:
	$(tf_cmd) output -raw $(name)

#Make lambda zip file in /terraform/zips directory. Whenever code gets changed in lamdba_typescript directory , new zip file gets uploaded to s3. For local,you can you this make target
lambda-zip:
	cd ../lambda_typescript && \
	chmod +x ./deploy.sh && \
	./deploy.sh

#Make catch-all-lambda zip file in /terraform/zips directory. Whenever code gets changed in lamdba_typescript directory , new zip file gets uploaded to s3. For local,you can you this make target
catch-all-zip:
	cd ../catch_all_lambda && \
	chmod +x ./deploy.sh && \
	./deploy.sh

import:
	$(tf_cmd) import $(tf_vars) $(to) $(id)

tf-%:
	$(tf_cmd) $*

.PHONY : lock-provider workspace init plan apply clean destroy output state-list lambda-zip catch-all-zip
