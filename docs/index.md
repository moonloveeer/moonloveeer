# QRL Wallet Documentation

Your guide to the quantum-resistant wallet, node, and developer tooling in this repository.

## Highlights

| Capability | Description |
| --- | --- |
| Wallet | Run the Flask-based wallet locally or via Docker with built-in `/healthz` checks and Web3 login. |
| Node | Operate the lightweight blockchain node, manage mempool, and experiment with mining rewards. |
| Security | Follow CSP, CSRF, rate limiting, and SBOM practices baked into the codebase and workflows. |
| CI/CD | Automated tests, coverage, security scans, SBOM generation, Docker publishing, and release artifacts. |

## Start Here

- [Overview](overview.md) – project goals, architecture, and roadmap context.
- [Wallet Quickstart](wallet/quickstart.md) – launch the wallet from source or container.
- [Node Setup](node/setup.md) – work with `NodeService` and blockchain data directories.
- [Mining Getting Started](mining/getting-started.md) – mine blocks via UI or script.

## Build & Ship

- [CI/CD Pipeline Overview](ci/overview.md) – workflows, artifacts, and release mechanics.
- [Testing Strategy](testing/strategy.md) – unit, property, concurrency, and fuzz tests plus auditing.
- [Security Hardening](security/hardening.md) – application safeguards, supply chain controls, deployment tips.

## Developer Resources

- [Wallet REST API](apis/wallet.md)
- [Developer Contributing Guide](developer/contributing.md)
- [WHITEPAPER](WHITEPAPER.md)
- Repository: <https://github.com/moonloveeer/moonloveeer>
