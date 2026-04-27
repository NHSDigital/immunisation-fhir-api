-include .env

apigee_environment ?= $(APIGEE_ENVIRONMENT)
environment        ?= $(ENVIRONMENT)
sub_environment    ?= $(SUB_ENVIRONMENT)
sub_environment_dir := $(if $(findstring pr-,$(sub_environment)),pr,$(sub_environment))
tf_var_file        := ../instance/environments/$(environment)/$(sub_environment_dir)/variables.tfvars
has_sub_environment_scope = $(shell awk -F= '/^has_sub_environment_scope/ { gsub(/[[:space:]]/, "", $$2); print $$2 }' "$(tf_var_file)")
workspace_name = $(if $(filter false,$(has_sub_environment_scope)),$(environment),$(sub_environment))

tf_cmd = AWS_PROFILE=$(AWS_PROFILE) terraform

bucket_name = $(if $(filter dev,$(environment)),immunisation-$(apigee_environment),immunisation-$(environment))-terraform-state-files

tf_state = \
  -backend-config="bucket=$(bucket_name)" \
  -backend-config="key=event-source-mappings/state"

tf_vars = \
  -var="sub_environment=$(sub_environment)" \
  -var-file="$(tf_var_file)"

init:
	$(tf_cmd) init $(tf_state) -upgrade

workspace:
	$(tf_cmd) workspace select -or-create $(workspace_name) && echo "Switched to workspace/environment: $(workspace_name)"

adopt: workspace
	ENVIRONMENT='$(environment)' SUB_ENVIRONMENT='$(sub_environment)' RESOURCE_SCOPE='$(workspace_name)' bash ../../utilities/scripts/adopt_event_source_mappings.sh $(tf_vars)

plan: workspace
	$(tf_cmd) plan $(tf_vars)

apply: workspace
	$(tf_cmd) apply $(tf_vars) --auto-approve

destroy: workspace
	$(tf_cmd) destroy $(tf_vars) -auto-approve
	$(tf_cmd) workspace select default
	$(tf_cmd) workspace delete $(workspace_name)

output:
	$(tf_cmd) output -raw $(name)

.PHONY : init workspace adopt plan apply destroy output
