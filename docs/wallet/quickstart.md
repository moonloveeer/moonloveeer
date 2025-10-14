# Wallet Quickstart

This guide walks through running the Flask-based web wallet provided in this repository.

## Prerequisites
- Python 3.12+
- `pip` and `virtualenv`
- Optional: Docker (for containerized usage)

## Run from source
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --require-hashes -r requirements.lock
python run_web_wallet.py --port 5001
```

Key features:
- Port selection logic in `run_web_wallet.py` honors the `--port` flag or `PORT` env var and scans for free ports.
- Wallet data persists under `WEB_WALLET_DATA_DIR` (defaults to `.web_wallet_data/`).

## Run with Docker
```bash
docker pull ghcr.io/moonloveeer/moonloveeer:latest
docker run --rm -p 5001:5001 -e PORT=5001 ghcr.io/moonloveeer/moonloveeer:latest
```

The container entrypoint launches Gunicorn with the Flask app (`qrl.web_wallet:app`) and exposes `/healthz` for readiness checks.
