PY := python3
PIP := $(PY) -m pip
VENV := .venv
PYTHON := $(VENV)/bin/python
PIPX := $(VENV)/bin/pip
PRECOMMIT := $(VENV)/bin/pre-commit

.DEFAULT_GOAL := help

$(VENV):
	$(PY) -m venv $(VENV)
	$(PIPX) install --upgrade pip
	$(PIPX) install pip-tools

help:
	@echo "Common targets: venv, install, lock, test, lint, run, docs-serve, docs-build, docker-build, docker-run, sbom, audit"

venv: $(VENV)

install: venv
	@# Prefer hashed lock installs, fallback to requirements.txt
	@if [ -f requirements.lock ]; then \
		$(PIPX) install --require-hashes -r requirements.lock; \
	else \
		$(PIPX) install -r requirements.txt; \
	fi

lock: venv
	$(VENV)/bin/pip-compile --allow-unsafe --generate-hashes -o requirements.lock requirements.txt

sync: venv
	@if [ -f requirements.lock ]; then \
		$(VENV)/bin/pip-sync requirements.lock; \
	else \
		$(PIPX) install -r requirements.txt; \
	fi

test: install
	$(VENV)/bin/pytest -vv -s --cov=qrl --cov-report=term-missing

lint: install
	$(PIPX) install pre-commit
	$(PRECOMMIT) run --all-files --show-diff-on-failure

run: install
	PORT?=5001
	$(PYTHON) run_web_wallet.py --port $(PORT)

docs-serve: install
	$(PIPX) install mkdocs
	$(VENV)/bin/mkdocs serve -a 0.0.0.0:8000

docs-build: install
	$(PIPX) install mkdocs
	$(VENV)/bin/mkdocs build --strict --site-dir site

sbom: install
	$(PIPX) install cyclonedx-bom
	$(VENV)/bin/cyclonedx-bom -o sbom.json -p pip -i requirements.lock

audit: install
	$(PIPX) install pip-audit bandit
	$(VENV)/bin/pip-audit -r requirements.lock || true
	$(VENV)/bin/bandit -q -r qrl || true

docker-build:
	docker build -t ghcr.io/moonloveeer/moonloveeer:dev .

docker-run:
	PORT?=5001
	docker run --rm -p $(PORT):$(PORT) -e PORT=$(PORT) ghcr.io/moonloveeer/moonloveeer:dev
