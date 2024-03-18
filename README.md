# immunisation-fhir-api

See `README.specification.md` for details of the API specification's development.

## Directories

```
backend     - The API code.
terraform   - Infrastructure.
tests       - Integration tests.
devtools    - Helper project for development.
```

See any readmes in those directories for more details.

## Spelling

Refer to the FHIR Immunization resource capitalised and with a "z" as FHIR is U.S. English.

All other uses are as British English i.e. "immunisation".

See https://nhsd-confluence.digital.nhs.uk/display/APM/Glossary.

## Setup for local dev

`backend` should have its own environment to keep it separate from the infrastructure and integration tests.

### Tools

Install `direnv` and `pyenv`.
https://direnv.net/docs/installation.html
https://github.com/pyenv/pyenv?tab=readme-ov-file#installation

These tools automate the Python version and environment creation and use, and selects them automatically when entering a
directory.  
`pyenv` separates Python versions and `direnv` handles the environment.
`direnv` uses `pyenv` to select the version and creates an environment under `.direnv/`.

At this point you'll get a warning when you enter this directory, telling you to run `direnv allow`. This is fine and
the next step will resolve it.

### Install Python versions and environments

This will set up for both the root and `backend`.

Rename `.env.default` to `.env` or merge it with your existing file.
Rename `.envrc.default` to `.envrc` or merge it with your existing file.

These are kept separate so other tools can use `.env` if wanted.

Edit `.env` with your details.

```shell
make setup-python-envs
poetry install --no-root
```

### IDEs

The `backend` tests are in a separate module so in order for them to see each other we need to let the IDE know
about the relationship.

#### IntelliJ

- Open the root repo directory in IntelliJ.
- In Project Structure add an existing virtualenv SDK for `.direnv/python-x.x.x/bin/python`.
- Set the project SDK and the default root module SDK to the one created above.
    - Add `tests` as sources.
    - Add `.direnv`, `terraform/.terraform`, and `terraform/build` as exclusions if they're not already.
- Add another existing virtualenv SDK for `backend/.direnv/python-x.x.x/bin/python`.
- Import a module pointed at the `backend` directory, set the SDK created above.
    - Add the `src` and `tests` directories as sources.
    - Add `.direnv` as an exclusion if it's not already.

#### VS Code

The project must be opened as a multi-root workspace for VS Code to know that `backend` has its own environment.

- Open the workspace `immunisation-fhir-api.code-workspace`.
- Copy `backend/.vscode/settings.json.default` to `backend/.vscode/settings.json`, or merge the contents with
  your existing file.

VS Code will automatically use the `backend` environment when you're editing a file under `backend`.

Depending on your existing setup VS Code might automatically choose the wrong virtualenvs. Change it
with `Python: Select Interpreter`.

The root (immunisation-fhir-api) should be pointing at `.direnv/python-x.x.x/bin/python.`

`backend` should be pointing at `backend/.direnv/python-x.x.x/bin/python.`

