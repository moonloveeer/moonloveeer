# Mining Getting Started

This section highlights mining behavior for the toy blockchain implementation.

## Overview
- Blocks are mined via `Blockchain.mine_pending_transactions()` inside `NodeService.mine_block()`.
- Mining rewards originate from a coinbase transaction (sender `"0"`).
- Difficulty is configurable in `qrl/core/blockchain.py` (default `difficulty=4`).

## Manual mining via wallet UI
1. Launch the wallet (`python run_web_wallet.py`).
2. Log in and click **Mine Block** (requires a wallet).
3. Pending transactions from the mempool are included, then rewards are credited to your address.

## Programmatic mining
```python
from qrl.services.node_service import NodeService

node = NodeService()
node.create_wallet()
node.mine_block()
```

For experiments, reduce difficulty or add fake transactions to observe reward halving logic.
