#!/bin/bash
asdf install
find . -name "pyproject.toml" -not -path '**/.venv/*' -execdir sh -c 'echo Running setup for $(pwd):; rm -rf .venv; python -m venv .venv; source .venv/bin/activate; poetry install --no-root; deactivate' \;
