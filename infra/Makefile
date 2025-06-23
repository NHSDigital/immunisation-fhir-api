-include .env

interactionId=$(ENVIRONMENT)

tf_cmd = AWS_PROFILE=$(AWS_PROFILE) terraform
tf_state= -backend-config="bucket=$(BUCKET_NAME)"
tf_vars= -var-file=environments/$(ENVIRONMENT)/variables.tfvars


.PHONY : lock-provider workspace init plan apply clean destroy output state-list lambda-zip catch-all-zip

lock-provider:
	# Run this only when you install a new terraform provider. This will generate sha code in lock file for all platform
	echo "This may take a while. Be patient!"
	$(tf_cmd) providers lock -platform=darwin_arm64 -platform=darwin_amd64 -platform=linux_amd64 -platform=windows_amd64

workspace:
	$(tf_cmd) workspace new $(ENVIRONMENT) || $(tf_cmd) workspace select $(ENVIRONMENT) && echo "Switched to workspace/environment: $(ENVIRONMENT)"

init:
	$(tf_cmd) init $(tf_state) -upgrade $(tf_vars)

plan: workspace
	 $(tf_cmd) plan $(tf_vars)

apply: workspace
	$(tf_cmd) apply $(tf_vars) -auto-approve

clean:
	rm -rf build .terraform upload-key

destroy: workspace
	$(tf_cmd) destroy $(tf_vars) -auto-approve
	$(tf_cmd) workspace select default
	$(tf_cmd) workspace delete $(ENVIRONMENT)

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

tf-%:
	$(tf_cmd) $*
