-include .env

environment = prod
workspace_name = backup-source

tf_cmd = AWS_PROFILE=$(AWS_PROFILE) terraform
tf_state = -backend-config="bucket=imms-$(environment)-terraform-state-files"

.PHONY: lock-provider workspace init init-reconfigure plan apply clean destroy import tf-%

lock-provider:
	# Run this only when you install a new terraform provider. This will generate sha code in lock file for all platform
	echo "This may take a while. Be patient!"
	$(tf_cmd) providers lock -platform=darwin_arm64 -platform=darwin_amd64 -platform=linux_amd64 -platform=windows_amd64

workspace:
	$(tf_cmd) workspace select -or-create $(workspace_name) && echo "Switched to workspace: $(workspace_name)"

init:
	$(tf_cmd) init $(tf_state) -upgrade $(tf_vars)

init-reconfigure:
	$(tf_cmd) init $(tf_state) -upgrade $(tf_vars) -reconfigure

plan: workspace
	 $(tf_cmd) plan $(tf_vars)

apply: workspace
	$(tf_cmd) apply $(tf_vars)

clean:
	rm -rf .terraform

destroy: workspace
	$(tf_cmd) destroy $(tf_vars)
	$(tf_cmd) workspace select default
	$(tf_cmd) workspace delete $(workspace_name)

import:
	$(tf_cmd) import $(tf_vars) $(to) $(id)

tf-%:
	$(tf_cmd) $*
