# Testing Strategy

Testing ensures correctness across consensus logic, cryptography, and the web wallet. We rely on layered techniques outlined below.

## Unit and integration tests
- `tests/test_blockchain.py`, `tests/test_transaction.py`, and related modules validate core blockchain behaviors (mining rewards, transaction validation).
- Wallet integration tests exercise Flask routes using test clients.
- CLI smoke tests (`tests/test_cli_commands.py`) patch `NodeService` and execute Click commands to ensure wallet generation, info, transfers, and mining toggles behave as expected.

## Property-based testing
- `tests/test_transaction_props.py` uses Hypothesis to probe invariant properties of transaction creation and validation, catching corner cases beyond hand-written tests.

## Concurrency testing
- `tests/test_ots_concurrency.py` stresses XMSS signing under concurrent threads to verify the locking around OTS index management.

## API fuzzing
- `tests/test_api_fuzz.py` generates randomized requests against wallet endpoints to ensure robust input validation and stable responses.

## Coverage and reporting
- Pytest runs with `--cov=qrl --cov-report=xml` in CI. Codecov ingests the XML report to track trends over time. Local developers can run `make test` to mirror the workflow.

## Continuous audit pipeline
- GitHub Actions executes pip-audit and bandit in the `security-audit` job (see `pytest.yml`).
- Trivy scans both the repository filesystem and Docker image for vulnerabilities; SARIF results surface in GitHub code scanning alerts.
- CodeQL analyzes Python sources for security issues on every push and pull request.

## Developer workflow tips
- Install `pre-commit` hooks via `make lint` to run Ruff and mypy before committing.
- Use the Makefile to regenerate lockfiles (`make lock`), execute tests, or serve docs locally.
- Run targeted pytest suites when modifying sensitive modules (e.g., cryptography or networking) to minimize regression risk.
