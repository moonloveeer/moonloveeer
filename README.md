# QRL - Quantum Resistant Ledger

A Layer-1 blockchain implementation with quantum-safe signatures (XMSS) and Proof-of-Work consensus.

## Features

- **Quantum-Safe Signatures**: Uses XMSS (eXtended Merkle Signature Scheme) for transaction signing, making it resistant to quantum computer attacks.
- **Proof-of-Work Consensus**: Implements a mining mechanism for block validation and chain security.
- **Bitcoin-like Halving**: Mining rewards halve every 210,000 blocks, similar to Bitcoin's scarcity model.
- **Blockchain Structure**: Complete blockchain implementation with blocks, transactions, and state management.
- **Wallet Management**: Create and manage wallets with secure key generation.
- **Transaction Processing**: Send and receive QRL tokens between wallets.
- **Blockchain Verification**: Ensures chain integrity and prevents tampering.

## Installation

1. Clone the repository
2. Run the installation script:

```bash
./install.sh
```

This will create a virtual environment and install all required dependencies.

Alternatively, you can manually set up the environment:

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

## Usage

### Quick Test

To quickly test the blockchain functionality:

```bash
python3 test_blockchain.py
```

To test transaction functionality between wallets:

```bash
python3 test_transaction.py
```

### Continuous Integration

Add the regression suites to your pipeline so they run on every push:

```
/Users/rain/Desktop/QRL/venv/bin/python -m pytest tests/test_wallet_send.py tests/test_api_endpoints.py
```

### Explorer Manual QA Checklist

- **Start server**: `python run_web_wallet.py` with the virtualenv activated.
- **Verify overview auto-refresh**: Observe the "Last updated" text and confirm it changes after 30 seconds or when clicking **Refresh**.
- **Load more blocks**: Use the **Load more** button in the Recent Blocks card and ensure additional rows render without layout issues.
- **Load more transactions**: Click **Load more** in the Transactions tab and confirm pending entries and confirmation badges update correctly.
- **API parity**: Compare on-page data with `curl "http://127.0.0.1:5001/api/blocks?count=5"` and `curl "http://127.0.0.1:5001/api/transactions?limit=10&pending=true"`.
- **Return navigation**: Confirm explorer links (`View`, `Details`, `Back to Wallet`) navigate as expected.

### Running a Node

Activate the virtual environment and start a node:

```bash
source venv/bin/activate
python3 -m qrl.main
```

To start mining:

```bash
python3 -m qrl.main --mine
```

### CLI Commands

The QRL CLI provides several commands for interacting with the blockchain:

```bash
# Generate a new wallet
python3 -m qrl.cli.commands wallet_gen

# Get wallet information
python3 -m qrl.cli.commands wallet_info

# Send a transaction
python3 -m qrl.cli.commands tx_transfer --dst <destination_address> --amount <amount>

# Mine a block
python3 -m qrl.cli.commands mining_start

# Get blockchain information
python3 -m qrl.cli.commands blockchain_info
```

## Project Structure

```
├── qrl/
│   ├── __init__.py
│   ├── main.py              # Main entry point for running the node
│   ├── config.py            # Configuration settings
│   ├── cli/                 # Command-line interface
│   │   ├── __init__.py
│   │   └── commands.py      # CLI commands implementation
│   ├── core/                # Core blockchain components
│   │   ├── __init__.py
│   │   ├── block.py         # Block structure
│   │   ├── blockchain.py    # Blockchain implementation
│   │   └── transaction.py   # Transaction structure
│   ├── crypto/              # Cryptographic functions
│   │   ├── __init__.py
│   │   └── xmss.py          # XMSS implementation
│   └── services/            # Service layer
│       ├── __init__.py
│       └── node_service.py  # Node service implementation
├── install.sh              # Installation script
├── requirements.txt        # Python dependencies
├── setup.py               # Package setup
├── test_blockchain.py     # Blockchain test script
└── test_transaction.py    # Transaction test script
```

## Data Storage

Blockchain data and wallet information are stored in the `~/.qrl/` directory by default:

- `~/.qrl/blockchain.json` - Contains the entire blockchain
- `~/.qrl/wallet.json` - Contains the wallet information

## Security Considerations

- This is a simplified implementation for educational purposes
- The XMSS implementation provides quantum resistance but should be reviewed for production use
- Private keys are stored in plain JSON files - a production system would need more secure storage

## License

MIT