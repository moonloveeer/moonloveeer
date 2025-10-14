# Node Setup

The node implementation lives in `qrl/services/node_service.py` and wraps blockchain, mempool, and network management components.

## Create a node instance
```python
from qrl.services.node_service import NodeService

node = NodeService(data_dir="~/.qrl", host="0.0.0.0", port=9000)
```

Key behaviors:
- Loads or initializes blockchain data from `blockchain.json` and wallet state from `wallet.json` under the configured data directory.
- Spawns a `NetworkManager` that handles peer discovery and message broadcasting.

## Running the async service
```python
import asyncio

async def main():
    node = NodeService()
    await node.start()

asyncio.run(main())
```

The service exposes `start()` / `stop()` coroutines and handles broadcasting new blocks and transactions.

## Configuration hints
- Data directory defaults to `~/.qrl`; set `WEB_WALLET_DATA_DIR` when launching the wallet UI to isolate dev data.
- Ports are configurable through the `NodeService` constructor.
- Wallet creation uses XMSS with configurable Merkle height via `create_wallet(height=10)`.
