# Security Hardening

Security controls implemented in this repository and recommended deployment practices.

## Application safeguards
- Strict CSP with nonce injection (`apply_security_headers()` in `qrl/web_wallet.py`).
- CSRF tokens issued per request; cookies marked `Secure`/`HttpOnly` when behind TLS.
- Rate limits on login-sensitive routes (`enforce_rate_limit()`).
- XMSS private-key locking to ensure one-time signature indices are not reused under concurrency.

## Supply chain
- Reproducible dependency management via `requirements.lock` (hashed) and `pip-compile`.
- CI generates a CycloneDX SBOM (`sbom.json`) in test and release workflows.
- Docker images built from `python:3.12-slim`, locked dependencies, and health checks.

## CI/CD security
- CodeQL, Trivy (FS + image), pip-audit, and bandit run in GitHub Actions.
- Release workflow signs artifacts through GitHub Releases and attaches SBOM + vendor wheel.

## Deployment guidance
- Set `SECRET_KEY`, `WEB_WALLET_DATA_DIR`, and disable `AUTO_MINE_ON_SEND` in production `.env`.
- Terminate TLS in front of the wallet; ensure `X-Forwarded-Proto` is set for secure cookie enforcement.
- Run the container with read-only root filesystem and a non-root user if deploying beyond dev.
- Enable logging aggregation and monitoring on `/healthz`.
