-include .env

apigee_environment ?= $(APIGEE_ENVIRONMENT)
environment        ?= $(ENVIRONMENT)
sub_environment    ?= $(SUB_ENVIRONMENT)
sub_environment_dir := $(if $(findstring pr-,$(sub_environment)),pr,$(sub_environment))
tf_var_file        := ../instance/environments/$(environment)/$(sub_environment_dir)/variables.tfvars
has_sub_environment_scope = $(shell sed -n 's/^[[:space:]]*has_sub_environment_scope[[:space:]]*=[[:space:]]*//p' "$(tf_var_file)" 2>/dev/null | sed 's/[[:space:]]*\#.*$$//' | tr -d '[:space:]' | sed -n '1p')
targets_requiring_tf_var_scope := init workspace adopt validate plan plan-ci apply apply-ci verify ensure-destroy-allowed destroy output
requested_targets := $(if $(MAKECMDGOALS),$(MAKECMDGOALS),init)
ifneq ($(filter $(targets_requiring_tf_var_scope),$(requested_targets)),)
ifeq ($(has_sub_environment_scope),)
$(error has_sub_environment_scope not found in $(tf_var_file))
endif
ifneq ($(filter true false,$(has_sub_environment_scope)),$(has_sub_environment_scope))
$(error has_sub_environment_scope in $(tf_var_file) must be true or false, got '$(has_sub_environment_scope)')
endif
endif
workspace_name = $(if $(filter false,$(has_sub_environment_scope)),$(environment),$(sub_environment))
allow_shared_scope_destroy ?= $(ALLOW_SHARED_SCOPE_DESTROY)

tf_cmd = AWS_PROFILE=$(AWS_PROFILE) terraform

bucket_name = $(if $(filter dev,$(environment)),immunisation-$(apigee_environment),immunisation-$(environment))-terraform-state-files

tf_state = -backend-config="bucket=$(bucket_name)"

tf_vars = \
  -var="sub_environment=$(sub_environment)" \
  -var-file="$(tf_var_file)"

init:
	$(tf_cmd) init $(tf_state) -upgrade

workspace:
	$(tf_cmd) workspace select -or-create $(workspace_name) && echo "Switched to workspace/environment: $(workspace_name)"

adopt: workspace
	ENVIRONMENT='$(environment)' SUB_ENVIRONMENT='$(sub_environment)' RESOURCE_SCOPE='$(workspace_name)' bash ../../utilities/scripts/adopt_event_source_mappings.sh $(tf_vars)

fmt-check:
	$(tf_cmd) fmt -check

validate: workspace
	$(tf_cmd) validate

plan: workspace
	$(tf_cmd) plan $(tf_vars)

plan-ci: workspace
	$(tf_cmd) plan $(tf_vars) -out=tfplan -input=false

apply: workspace
	$(tf_cmd) apply $(tf_vars) --auto-approve

apply-ci: workspace
	$(tf_cmd) apply $(tf_vars) -input=false tfplan

verify:
	ENVIRONMENT='$(environment)' SUB_ENVIRONMENT='$(sub_environment)' RESOURCE_SCOPE='$(workspace_name)' EVENT_SOURCE_MAPPING_ACTION=verify bash ../../utilities/scripts/adopt_event_source_mappings.sh

ensure-destroy-allowed:
	@if [ "$(has_sub_environment_scope)" = "false" ] && [ "$(allow_shared_scope_destroy)" != "true" ]; then \
		echo "Refusing to destroy shared event source mappings in workspace $(workspace_name). Set ALLOW_SHARED_SCOPE_DESTROY=true for controlled teardown."; \
		exit 1; \
	fi

destroy: workspace ensure-destroy-allowed
	$(tf_cmd) destroy $(tf_vars) -auto-approve
	$(tf_cmd) workspace select default
	$(tf_cmd) workspace delete $(workspace_name)

output:
	$(tf_cmd) output -raw $(name)

.PHONY : init workspace adopt fmt-check validate plan plan-ci apply apply-ci verify ensure-destroy-allowed destroy output
