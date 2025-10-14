# CI/CD Overview

This project relies on GitHub Actions workflows to maintain quality, security, and release automation.

## Workflows
- `pytest.yml` – Executes unit/property tests, enforces hashed lockfile installs, uploads coverage to Codecov, produces SBOM artifacts, runs linting, and includes a `security-audit` job (pip-audit + bandit).
- `docker-publish.yml` – Builds the Docker image, performs a `/healthz` smoke test, then pushes to GHCR (`ghcr.io/moonloveeer/moonloveeer`).
- `release.yml` – On tags (`v*`), generates `requirements.lock` and `sbom.json`, builds the vendored `pyqrllib` wheel, and attaches all artifacts to the GitHub Release.
- `docs.yml` – Builds MkDocs Material docs, copying `README.md` to `docs/overview.md`, and deploys to GitHub Pages.
- `codeql.yml` – Runs CodeQL static analysis (Python).
- `trivy.yml` – Executes Trivy filesystem and container scans, uploading SARIF reports to GitHub code scanning.

## Key practices
- **Concurrency guards**: Each workflow defines `concurrency` groups to cancel overlapping runs.
- **Permissions**: Workflows set least-privilege permissions (e.g., `packages: write` for Docker publish only).
- **Artifacts**: Logs, SBOMs, and security reports are stored as artifacts for follow-up.
- **Tokenless Codecov upload**: Covered via OIDC permissions—coming soon if not already configured.

## Deployment pipeline
Container images are the deployment artifact. Downstream environments (Fly.io, K8s, etc.) can pull from GHCR.

Future enhancements might include environment promotion workflows or automated deployments once a target platform is chosen.
