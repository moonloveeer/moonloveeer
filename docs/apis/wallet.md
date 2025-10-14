# Wallet REST API

The Flask app defined in `qrl/web_wallet.py` exposes several REST endpoints under `/api`. This page summarizes the most important routes.

## Authentication
- Session cookies (`auth_token`) are set after Web3 login or password login.
- CSRF tokens are issued via `XSRF-TOKEN` cookie generated in `apply_security_headers()`.

## Endpoints

### `GET /api/transactions`
Query parameters:
- `limit` (int, optional) – number of transactions to return.
- `pending` (bool, optional) – include pending transactions from the mempool.

Returns JSON with a `transactions` list combining confirmed and optionally pending entries.

### `GET /api/blocks`
Parameters:
- `count` (int, optional) – number of recent blocks to return.

Responds with block summaries derived from `NodeService.get_blockchain_info()` and `node_service.blockchain.chain`.

### `GET /api/wallet/<address>`
Returns wallet information and current balance for the provided address. Addresses may be QRL or 0x-format; see validation logic in `TransferForm.validate_recipient()`.

### Web3 login flow
- `POST /web3/init-login` issues a nonce.
- `POST /web3/verify` validates the signature, seeds demo balance (if configured), and returns a JWT token.
- `GET /web3/verify-callback` supports browser navigation fallback after signature capture.

### Mining helpers
- `POST /mine` (protected) auto-mines pending transactions if `AUTO_MINE_ON_SEND` is enabled.

## Rate limiting
`enforce_rate_limit()` uses in-memory deques keyed by client IP to protect `web3_init`, `web3_verify`, and `mine` routes.

## Health check
- `GET /healthz` responds with status for readiness probes. The Docker `HEALTHCHECK` and CI smoke test hit this endpoint.
