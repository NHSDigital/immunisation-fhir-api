# immunisation-fhir-api

See `README.specification.md` for details of the API specification's development.

## Spelling

Refer to the FHIR Immunization resource capitalised and with a "z" as FHIR is U.S. English.

All other uses are as British English i.e. "immunisation".

See https://nhsd-confluence.digital.nhs.uk/display/APM/Glossary.

## Directories
**Note:** Each Lambda has its own `README.md` file for detailed documentation. For non-Lambda-specific folders, refer to `README.specification.md`.

### Lambdas

| Folder              | Description |
|---------------------|-------------|
| `backend`           | **Imms API** – Handles CRUD operations for the Immunisation API. |
| `delta_backend`     | **Imms Sync** – Lambda function that reacts to events in the Immunisation database. |
| `ack_backend`       | **Imms Batch** – Generates the final Business Acknowledgment (BUSACK) file from processed messages and writes it to the designated S3 location. |
| `filenameprocessor` | **Imms Batch** – Processes batch file names. |
| `mesh_processor`    | **Imms Batch** – MESH-specific batch processing functionality. |
| `recordprocessor`   | **Imms Batch** – Handles batch record processing. |
| `redis_sync`        | **Imms Redis** – Handles sync s3 to REDIS. |
---

### Pipelines

| Folder  | Description |
|---------|-------------|
| `azure` | Pipeline definition and orchestration code. |

---

### Infrastructure

| Folder                | Description |
|------------------------|-------------|
| `infra`                | Base infrastructure components. |
| `infra_old`            | Old infra code used to create INT to mimic prod. |
| `grafana`              | Terraform configuration for Grafana, built on top of core infra. |
| `terraform`            | Core Terraform infrastructure code. This is run in each PR and sets up lambdas associated with the PR.|
| `terraform_old`        | Old tf code used to create INT to mimic prod. |
| `terraform_sandbox`    | Sandbox environment for testing infrastructure changes. |
| `terraform_aws_backup` | Streamlined backup processing with AWS. |
| `mesh-infra`           | Infrastructure setup for Imms batch MESH integration. |
| `proxies`              | Apigee API proxy definitions. |
---

### Tests

| Folder        | Description |
|---------------|-------------|
| `e2e`         | End-to-end tests executed during PR pipelines. |
| `e2e_batch`   | E2E tests specifically for batch-related functionality, also run in the PR pipeline. |
| `tests`   | Sample e2e test. |
---

### Utilities

| Folder         | Description |
|----------------|-------------|
| `devtools`      | Helper tools and utilities for local development |
| `scripts`       | Standalone or reusable scripts for development and automation |
| `specification` | Specification files to document API and related definitions |
| `sandbox` | Simple sandbox API |

---

## Background: Python Package Management and Virtual Environments
- `pyenv` manages multiple Python versions at the system level, allowing you to install and switch between different Python versions for different projects.
- `direnv` automates the loading of environment variables and can auto-activate virtual environments (.venv) when entering a project directory, making workflows smoother.
- `.venv` (created via python -m venv or poetry) is Python’s built-in tool for isolating dependencies per project, ensuring that packages don’t interfere with global Python packages.
- `Poetry` is an all-in-one dependency and virtual environment manager that automatically creates a virtual environment (.venv), manages package installations, and locks dependencies (poetry.lock) for reproducibility, making it superior to using pip manually and it is used in all the lambda projects. 

## Project structure 
To support a modular and maintainable architecture, each Lambda function in this project is structured as a self-contained folder with its own dependencies, configuration, and environment. 

We use Poetry to manage dependencies and virtual environments, with the virtualenvs.in-project setting enabled to ensure each Lambda has an isolated `.venv` created within its folder. 

Additionally, direnv is used alongside `.envrc` and `.env` files to automatically activate the appropriate virtual environment and load environment-specific variables when entering a folder. 

Each Lambda folder includes its own `.env` file for Lambda-specific settings, while the project root contains a separate `.env` and `.venv` for managing shared tooling, scripts, or infrastructure-related configurations. This setup promotes clear separation of concerns, reproducibility across environments, and simplifies local development, testing, and packaging for deployment.

## Environment setup
These dependencies are required for running and debugging the Lambda functions and end-to-end (E2E) tests.

### Install dependencies 
Steps: 
1. Install [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) if running on Windows and install [Docker](https://docs.docker.com/engine/install/).
2. Install the following tools inside WSL. These will be used by the lambda and infrastructure code:
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)

3. Open VS Code and click the bottom-left corner (blue section), then select **"Connect to WSL"** and choose your WSL distro (e.g., `Ubuntu-24.04`).
Once connected, you should see the path as something similar to: `/mnt/d/Source/immunisation-fhir-api/backend`.
4. Run the following commands to install dependencies
    ```
    sudo apt update && sudo apt upgrade -y
    sudo apt install -y make build-essential libssl-dev zlib1g-dev \
        libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
        libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev \
        liblzma-dev git libgdbm-dev libgdbm-compat-dev
    pip install --upgrade pip
    ```

5. Configure pyenv.
    ```
    pyenv install --list | grep "3.10"
    pyenv install 3.10.16 #current latest
    ```

6. Install poetry 
    ```
    pip install poetry
    ```

### Setting up a virtual environment with poetry
The steps below must be performed in each Lambda function folder and e2e folder to ensure the environment is correctly configured.

For detailed instructions on running individual Lambdas, refer to the README.md files located inside each respective Lambda folder.

Steps: 
1. Set the python version in the folder with the code used by lambda for example `./backend` (see [lambdas](#lambdas)) folder.
    ```
    pyenv local 3.10.16 # Set version in backend (this creates a .python-version file)
    ```

2. Configure poetry
    ```
    ### Point poetry virtual environment to .venv
    poetry config virtualenvs.in-project true
    poetry env use $(pyenv which python)
    poetry env info
    ```

3. Create an .env file and add environment variables.
    ```
    AWS_PROFILE={your_profile}
    IMMUNIZATION_ENV=local
    ```

4. Configure `direnv` by creating a `.envrc` file in the backend folder. This points direnv to the `.venv` created by poetry and loads env variables specified in the `.env` file
    ```
    export VIRTUAL_ENV=".venv"
    PATH_add "$VIRTUAL_ENV/bin"

    dotenv
    ```

5. Restart bash and run `direnv allow`. You should see something similar like: 
    ```
    direnv: loading /mnt/d/Source/immunisation-fhir-api/.envrc
    direnv: export +AWS_PROFILE +IMMUNIZATION_ENV +VIRTUAL_ENV ~PATH
    ```
    Test if environment variables have been loaded into shell: `echo $IMMUNIZATION_ENV`.

### Setting up the root level environment
The root-level virtual environment is primarily used for linting, as we create separate virtual environments for each folder that contains Lambda functions.
Steps: 
1. Follow instructions above to [install dependencies](#install-dependencies) & [set up a virtual environment](#setting-up-a-virtual-environment-with-poetry). 
**Note: While this project uses Python 3.10 (e.g. for Lambdas), the NHSDigital/api-management-utils repository — which orchestrates setup and linting — defaults to Python 3.8.
The linting command is executed from within that repo but calls the Makefile in this project, so be aware of potential Python version mismatches when running or debugging locally or in the pipeline.**
2. Run `make lint`. This will:
    - Check the linting of the API specification yaml.
    - Run Flake8 on all Python files in the repository, excluding files inside .venv and .terraform directories.

## IDE setup 
The current team uses VS Code mainly. So this setup is targeted towards VS code. If you use another IDE please add the documentation to set up workspaces here.

### VS Code

The project must be opened as a multi-root workspace for VS Code to know that `backend` has its own environment.

- Open the workspace `immunisation-fhir-api.code-workspace`.
- Copy `backend/.vscode/settings.json.default` to `backend/.vscode/settings.json`, or merge the contents with
  your existing file.

VS Code will automatically use the `backend` environment when you're editing a file under `backend`.

Depending on your existing setup VS Code might automatically choose the wrong virtualenvs. Change it
with `Python: Select Interpreter`.

The root (`immunisation-fhir-api`) should point to `/mnt/d/Source/immunisation-fhir-api/.venv/bin/python`.

`backend` should be pointing at `/mnt/d/Source/immunisation-fhir-api/backend/.venv/bin/python`

### IntelliJ

- Open the root repo directory in IntelliJ.
- In Project Structure add an existing virtualenv SDK for `.direnv/python-x.x.x/bin/python`.
- Set the project SDK and the default root module SDK to the one created above.
    - Add `tests` as sources.
    - Add `.direnv`, `terraform/.terraform`, and `terraform/build` as exclusions if they're not already.
- Add another existing virtualenv SDK for `backend/.direnv/python-x.x.x/bin/python`.
- Import a module pointed at the `backend` directory, set the SDK created above.
    - Add the `src` and `tests` directories as sources.
    - Add `.direnv` as an exclusion if it's not already.


## Verified commits
Please note that this project requires that all commits are verified using a GPG key. 
To set up a GPG key please follow the instructions specified here:
https://docs.github.com/en/authentication/managing-commit-signature-verification