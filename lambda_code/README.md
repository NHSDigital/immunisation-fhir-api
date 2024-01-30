# immunisation-fhir-api lambda

Comment for testing MTLS configuration

## Setup for local dev

The tests are in a separate module so in order for them to see each other we need to let the IDE know about the relationship.

### IntelliJ

- Open the root repo directory in IntelliJ.
- Set up the SDK as you see fit.
    - One option is direnv and pyenv with an `.envrc` of `layout pyenv 3.8.10`.
      Then add an existing virtualenv SDK in the project settings for `.direnv/python-3.8.10/bin/python`  
      You likely want separate environments for the root and for `lambda_code`.
- Add a new module of the `lambda_code` directory to the Project Structure, using the SDK created above. Add the `src` and `tests` directories as sources.


### VS Code

- Open the root repo directory in VS Code.
- Copy `.vscode/settings.json.default` to `.vscode/settings.json`, or integrate the contents with your existing file.
- Run the `Python: Configure Tests` command and when it asks for a directory give it `lambda_code`.


## Troubleshooting

### Tests fail with `No products grant access to proxy [...]`

Products are handled by the infra template and get cleaned up periodically.
Running `/azp run` on the PR should fix it.


### Terraform unable to create Cloudwatch Log Group

`Error: creating CloudWatch Logs Log Group (/aws/lambda/imms-pr-66_create_imms): operation error CloudWatch Logs: CreateLogGroup, https response error StatusCode: 400, RequestID: aa314084-220d-44d6-91ac-f6d8b76b428d, ResourceAlreadyExistsException: The specified log group already exists`

The switch from a Lambda package to a Docker image breaks the Log Group creation.
Seemingly because the log groups were not previously part of the state.
Fix by manually deleting the log groups for your workspace before applying the Terraform.
