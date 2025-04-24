#!/bin/bash
asdf install
find . -name "pyproject.toml" -not -path '**/.venv/*' -execdir sh -c 'echo Running setup for $(pwd):; python -m venv .venv; poetry install --no-root' \;
