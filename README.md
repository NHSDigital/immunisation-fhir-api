# immunisation-fhir-api

See `README.specification.md` for details of the API specification's development.

## Spelling

Refer to the FHIR Immunization resource capitalised and with a "z" as FHIR is U.S. English.

All other uses are as British English i.e. "immunisation".

See https://nhsd-confluence.digital.nhs.uk/display/APM/Glossary.

## Directories

**Note:** Each Lambda has its own `README.md` file for detailed documentation. For non-Lambda-specific folders, refer to `README.specification.md`.

### Lambdas (compute microservices)

| Folder                   | Description                                                                                                                                                                             |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ack_backend`            | **Imms Batch** – Generates the final Business Acknowledgment (BUSACK) file from processed messages and writes it to the designated destination.                                         |
| `backend`                | **Imms API** – Handles CRUD operations for the Immunisation API.                                                                                                                        |
| `batch_processor_filter` | **Imms Batch** – Controller function that consumes from a queue and forwards file event for processing if filter conditions are met.                                                    |
| `delta_backend`          | **Imms Sync** – Lambda function that reacts to events in the Immunisation Event Data Store (IEDS).                                                                                      |
| `filenameprocessor`      | **Imms Batch** – Validates and processes new batch file events.                                                                                                                         |
| `id_sync`                | **Imms Cross-cutting** – Handles [MNS](https://digital.nhs.uk/developer/api-catalogue/multicast-notification-service) NHS Number Change events and applies updates to affected records. |
| `mesh_processor`         | **Imms Batch** – Triggered when new files are received via MESH. Moves them into the Imms Batch processing system.                                                                      |
| `mns_subscription`       | **Imms Cross-cutting** – Simple helper Lambda which sets up our required MNS subscription. Used in pipelines in DEV.                                                                    |
| `recordforwarder`        | **Imms Batch** – Consumes from the stream and applies the processed batch file row operations (CUD) to IEDS.                                                                            |
| `recordprocessor`        | **Imms Batch** – ECS Task - **not** a Lambda function - responsible for processing batch file rows and forwarding to the stream.                                                        |
| `redis_sync`             | **Imms Cross-cutting** – Handles config file updates. E.g. disease mapping or permission files.                                                                                         |
| `shared`                 | **Imms Cross-cutting** – Shared `common` code that can be shared by other Lambda functions. This is not a standalone Lambda.                                                            |

---

### Pipelines

Due to the timing of the project's inception, Azure pipelines have been inherited from the API Management team for deploying
the Apigee proxy and sandbox. The new way to manage and deploy said resources is [Proxygen](https://digital.nhs.uk/developer/api-catalogue/proxy-generator).

In future a migration plan will be provided by the API Management team so we can move to the new process and use purely
GitHub Actions for our entire pipeline.

| Folder    | Description                                                                                                                     |
| --------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `azure`   | Pipeline definition and orchestration code concerned purely with the management and deployment of the Apigee proxy and sandbox. |
| `.github` | Pipeline definition and orchestration code for deploying and testing our backend project.                                       |

---

### Infrastructure

| Folder                 | Description                                                     |
| ---------------------- | --------------------------------------------------------------- |
| `account`              | Base infrastructure components deployed on a per account basis. |
| `instance`             | Core Terraform app infrastructure.                              |
| `terraform_aws_backup` | Streamlined backup processing with AWS.                         |
| `proxies`              | Apigee API proxy definitions.                                   |

---

### Tests

| Folder           | Description                                                                   |
| ---------------- | ----------------------------------------------------------------------------- |
| `e2e_automation` | End-to-end tests executed during PR pipelines using the pytest-bdd framework. |

---

### Utilities

| Folder              | Description                                                   |
| ------------------- | ------------------------------------------------------------- |
| `quality_checks`    | Dependencies for linting and formatting Python code           |
| `utilities/scripts` | Standalone or reusable scripts for development and automation |
| `specification`     | Specification files to document API and related definitions   |
| `sandbox`           | Simple sandbox API                                            |

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
    pyenv install --list | grep "3.11"
    pyenv install 3.11.13 #current latest
    ```

6. Install direnv if not already present, and hook it to the shell.

    ```
    sudo apt-get update && sudo apt-get install direnv
    echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
    ```

7. Install poetry

    ```
    pip install poetry
    ```

8. Install pre-commit hooks. Ensure you have installed nodejs at the same version or later as per .tool-versions and
   then, from the repo root, run:
    ```
    npm install
    ```

### Setting up a virtual environment with poetry

The steps below must be performed in each Lambda function folder and e2e_automation folder to ensure the environment is correctly configured.

For detailed instructions on running individual Lambdas, refer to the README.md files located inside each respective Lambda folder.

Steps:

1. Set the python version in the folder with the code used by lambda for example `./backend` (see [lambdas](#lambdas)) folder.

    ```
    pyenv local 3.11.13 # Set version in backend (this creates a .python-version file)
    ```

    Note: consult the lambda's `pyproject.toml` file to get the required Python version for this lambda. At the time of writing, this is `~3.10` for the batch lambdas and `~3.11` for all the others.

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

    For unit tests to run successfully, you may also need to add an environment variable for PYTHONPATH. This should be:

    ```
    PYTHONPATH=src:tests
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

#### Running Unit Tests from the Command Line

It is not necessary to activate the virtual environment (using `source .venv/bin/activate`) before running a unit test suite from the command line; `direnv` will pick up the correct configurations for us. Run `pip list` to verify that the expected packages are installed. You should for example see that `recordprocessor` is specifically running `moto` v4, regardless of which if any `.venv` is active.

### Setting up the root level environment

The root-level virtual environment is primarily used for linting, as we create separate virtual environments for each folder that contains Lambda functions.
Steps:

1. Follow instructions above to [install dependencies](#install-dependencies) & [set up a virtual environment](#setting-up-a-virtual-environment-with-poetry).
   **Note: While this project uses Python 3.11 (e.g. for Lambdas), the NHSDigital/api-management-utils repository — which orchestrates setup and linting — defaults to Python 3.8.
   The linting command is executed from within that repo but calls the Makefile in this project, so be aware of potential Python version mismatches when running or debugging locally or in the pipeline.**
2. Run `make lint`. This will:
    - Check the linting of the API specification yaml.
    - Run Flake8 on all Python files in the repository, excluding files inside .venv and .terraform directories.

## IDE setup

The current team uses VS Code mainly. So this setup is targeted towards VS code. If you use another IDE please add the documentation to set up workspaces here.

### VS Code

The project must be opened as a multi-root workspace for VS Code to know that specific lambdas (e.g. `backend`) have their own environment.
This example is for `backend`; substitute another lambda name in where applicable.

- Open the workspace `immunisation-fhir-api.code-workspace`.
- Copy `backend/.vscode/settings.json.default` to `backend/.vscode/settings.json`, or merge the contents with
  your existing file.
- Similarly, copy or merge `backend/.vscode/launch.json.default` to `backend/.vscode/launch.json`.

VS Code will automatically use the `backend` environment when you're editing a file under `backend`.

Depending on your existing setup VS Code might automatically choose the wrong virtualenvs. Change it
with `Python: Select Interpreter`.

The root (`immunisation-fhir-api`) should point to the root `.venv`, e.g. `/mnt/d/Source/immunisation-fhir-api/.venv/bin/python`.

Meanwhile, `backend` should be pointing at (e.g.) `/mnt/d/Source/immunisation-fhir-api/backend/.venv/bin/python`

#### Running Unit Tests

Note that unit tests can be run from the command line without VSCode configuration.

In order that VSCode can resolve modules in unit tests, it needs the PYTHONPATH. This should be setup in `backend/.vscode/launch.json` (see above).

**NOTE:** In order to run unit test suites, you may need to manually switch to the correct virtual environment each time you wish to
run a different set of tests. To do this:

- Show and Run Commands (Ctrl-Shift-P on Windows)
    - Python: Create Environment
    - Venv
    - Select the `.venv` named for the test suite you wish to run, e.g. `backend`
    - Use Existing
- VSCode should now display a toast saying that the following environment is selected:
    - (e.g.) `/mnt/d/Source/immunisation-fhir-api/backend/.venv/bin/python`

### IntelliJ

- Open the root repo directory in IntelliJ.
- In Project Structure add an existing virtualenv SDK for `.direnv/python-x.x.x/bin/python`.
- Set the project SDK and the default root module SDK to the one created above.
    - Add `tests` as sources.
    - Add `.direnv`, `infrastructure/instance/.terraform`, and `infrastructure/instance/build`
      as exclusions if they're not already.
- Add another existing virtualenv SDK for `backend/.direnv/python-x.x.x/bin/python`.
- Import a module pointed at the `backend` directory, set the SDK created above.
    - Add the `src` and `tests` directories as sources.
    - Add `.direnv` as an exclusion if it's not already.

## Verified commits

Please note that this project requires that all commits are verified using a GPG key.
To set up a GPG key please follow the instructions specified here:
https://docs.github.com/en/authentication/managing-commit-signature-verification

## AWS configuration: getting credentials for AWS federated user accounts

If you need to run commands that interact with AWS resources e.g. running a terraform plan against a dev account locally
then you will need to configure AWS credentials.

Once you have been granted access, the `Access Keys` section within the AWS Access Portal will present you with several
options. It is _recommended_ to use `Option 2: Add a profile to your AWS credentials file`.

This is because the way that Python unittests using `moto` have been implemented is brittle and cannot handle other methods
such as IAM Identity Centre SSO. In future, we should consider following [moto recommendations](https://docs.getmoto.org/en/latest/docs/getting_started.html#how-do-i-avoid-tests-from-mutating-my-real-infrastructure)
to ensure our tests are authentication type agnostic and are fully robust.

If you _are_ using another option, such as SSO, and want to run unit tests then you will need to:

- Add dummy values for `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` to the .env file in the Lambda dir you are testing.
- Ensure those values are set before running the test
