# Developer Guide

This project emphasizes cryptographic correctness, reproducible builds, and CI transparency. Key practices:

## Environment setup
- Clone the repository and run `make venv && make install` to prepare the virtualenv with hashed requirements.
- Use the Makefile targets (`make test`, `make lint`, `make docs-build`) to align local workflows with CI.

## Pre-commit and linting
- `pre-commit` runs Ruff (lint + format), mypy, and basic hygiene hooks. Install with `make lint` or `pre-commit install` to enforce checks locally.

## Tests
- Unit tests live in `tests/` and include property-based suites (`tests/test_transaction_props.py`), concurrency coverage (`tests/test_ots_concurrency.py`), and REST fuzzing (`tests/test_api_fuzz.py`).
- CI runs `pytest -vv -s --cov=qrl --cov-report=xml`; view coverage trends on Codecov.

## Release flow
- Tagging `v*` triggers the release workflow to attach `requirements.lock`, `sbom.json`, and the vendored `pyqrllib` wheel.
- Docker images publish to GHCR with `/healthz` smoke tests.

## Documentation
- MkDocs builds run via GitHub Pages. Use Material markdown features (admonitions, tabs) for richer docs.
