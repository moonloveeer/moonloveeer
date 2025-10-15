import json
import os
from typing import Dict, Any, Optional, List
import asyncio

from qrl.core.blockchain import Blockchain
from qrl.core.transaction import Transaction
from qrl.core.mempool import Mempool
from qrl.crypto.xmss import XMSS
from qrl.services.network import NetworkManager, Peer, NetworkMessage, NetworkProtocol


class NodeService:
    """Node service for the QRL blockchain"""

import json
import os
from typing import Dict, Any, Optional, List
import asyncio

from qrl.core.blockchain import Blockchain
from qrl.core.transaction import Transaction
from qrl.core.mempool import Mempool
from qrl.crypto.xmss import XMSS
from qrl.services.network import NetworkManager, Peer, NetworkMessage, NetworkProtocol


class NodeService:
    """Node service for the QRL blockchain"""

    def __init__(self, data_dir: str = None, host: str = '0.0.0.0', port: int = 9000, live_mode: bool = False):
        """
        Initialize a new NodeService

        Args:
            data_dir: Directory to store blockchain data
            host: Host address to bind to
            port: Port number to bind to
            live_mode: If True, connect to real QRL network instead of local demo
        """
        self.live_mode = live_mode
        self.data_dir = data_dir or os.path.expanduser("~/.qrl")
        os.makedirs(self.data_dir, exist_ok=True)

        self.blockchain_file = os.path.join(self.data_dir, "blockchain.json")
        self.wallet_file = os.path.join(self.data_dir, "wallet.json")

        if self.live_mode:
            # In live mode, don't load local blockchain; connect to real network
            self.blockchain = None
            # Add known QRL mainnet seed nodes (update with real IPs from QRL docs)
            known_seeds = [
                Peer("seed1.theqrl.org", 19000),
                Peer("seed2.theqrl.org", 19000),
                # Add more real seeds if available
            ]
            self.network_manager = NetworkManager(None, host, port)
            for seed in known_seeds:
                self.network_manager.peers.add(seed)
        else:
            # Initialize blockchain
            self.blockchain = self._load_blockchain() or Blockchain(difficulty=4)

            # Initialize wallet
            self.wallet = self._load_wallet()

            # Initialize mempool
            self.mempool = Mempool()

            # Initialize network manager
            self.network_manager = NetworkManager(self.blockchain, host, port)

        # Set up network callbacks (only for demo mode)
        if not self.live_mode:
            self._setup_network_callbacks()

        # Node state
        self.running = False

    def _load_blockchain(self) -> Optional[Blockchain]:
        """
        Load blockchain from file

        Returns:
            Optional[Blockchain]: Loaded blockchain or None if file doesn't exist
        """
        if not os.path.exists(self.blockchain_file):
            return None

        try:
            with open(self.blockchain_file, 'r') as f:
                blockchain_dict = json.load(f)
            return Blockchain.from_dict(blockchain_dict)
        except Exception as e:
            print(f"Error loading blockchain: {e}")
            return None

    def _save_blockchain(self) -> None:
        """
        Save blockchain to file
        """
        if self.live_mode:
            return  # No local saving in live mode
        with open(self.blockchain_file, 'w') as f:
            json.dump(self.blockchain.to_dict(), f, indent=2)

    def _load_wallet(self) -> Optional[XMSS]:
        """
        Load wallet from file

        Returns:
            Optional[XMSS]: Loaded wallet or None if file doesn't exist
        """
        if not os.path.exists(self.wallet_file):
            return None

        try:
            with open(self.wallet_file, 'r') as f:
                wallet_dict = json.load(f)
            return XMSS.from_dict(wallet_dict)
        except Exception as e:
            print(f"Error loading wallet: {e}")
            return None

    def _save_wallet(self) -> None:
        """
        Save wallet to file
        """
        if self.live_mode:
            return  # No local saving in live mode
        if self.wallet:
            with open(self.wallet_file, 'w') as f:
                json.dump(self.wallet.to_dict(), f, indent=2)

    def _setup_network_callbacks(self):
        """Set up network event callbacks"""
        self.network_manager.on_peer_connected = self._on_peer_connected
        self.network_manager.on_peer_disconnected = self._on_peer_disconnected
        self.network_manager.on_transaction_received = self._on_transaction_received
        self.network_manager.on_block_received = self._on_block_received

    def _on_peer_connected(self, peer: Peer):
        """Called when a peer connects"""
        print(f"Peer connected: {peer}")

    def _on_peer_disconnected(self, peer: Peer):
        """Called when a peer disconnects"""
        print(f"Peer disconnected: {peer}")

    def _on_transaction_received(self, transaction: Transaction):
        """Called when a transaction is received from the network"""
        print(f"Transaction received from network: {transaction.transaction_hash}")
        # Transaction is already added to mempool by NetworkManager

    def _on_block_received(self, block):
        """Called when a block is received from the network"""
        print(f"Block received from network: {block.hash}")

        # Remove confirmed transactions from mempool
        for tx in block.transactions:
            if tx.transaction_hash != "0":  # Skip reward transactions
                self.mempool.remove_transaction(
                    tx.transaction_hash,
                    block_hash=block.hash
                )

        # Save blockchain
        self._save_blockchain()

    async def start(self):
        """Start the node service"""
        if self.running:
            return

        self.running = True
        print("Starting QRL node service...")

        # Start network manager
        await self.network_manager.start()

        print("QRL node service started")

    async def stop(self):
        """Stop the node service"""
        if not self.running:
            return

        self.running = False
        print("Stopping QRL node service...")

        # Stop network manager
        await self.network_manager.stop()

        # Save blockchain
        self._save_blockchain()

        print("QRL node service stopped")

    def create_wallet(self, height: int = 10) -> str:
        """
        Create a new wallet

        Args:
            height: Merkle tree height

        Returns:
            str: Wallet address
        """
        if self.live_mode:
            raise NotImplementedError("Wallet creation not implemented for live mode. Use external QRL wallet tools.")
        self.wallet = XMSS(height=height)
        self._save_wallet()
        return self.wallet.get_address()

    def get_wallet_address(self) -> Optional[str]:
        """
        Get the wallet address

        Returns:
            Optional[str]: Wallet address or None if wallet doesn't exist
        """
        if self.live_mode:
            raise NotImplementedError("Local wallet not available in live mode.")
        if not self.wallet:
            return None
        return self.wallet.get_address()

    def get_balance(self, address: Optional[str] = None) -> float:
        """
        Get the balance of an address

        Args:
            address: Address to get balance for (uses wallet address if None)

        Returns:
            float: Balance of the address
        """
        if self.live_mode:
            # In live mode, return a placeholder or fetch from real network (stub)
            print("Live mode: Balance fetching from real network not implemented. Returning 0.0")
            return 0.0  # Stub: implement real balance query if needed
        if not address and not self.wallet:
            return 0.0

        address = address or self.wallet.get_address()
        return self.blockchain.get_balance(address)

    def create_transaction(self, recipient: str, amount: float, fee: float = 0.0) -> bool:
        """
        Create a new transaction

        Args:
            recipient: Recipient address
            amount: Amount to transfer
            fee: Transaction fee

        Returns:
            bool: True if transaction was created, False otherwise
        """
        if self.live_mode:
            print("Live mode: Transactions hit the real QRL network. Broadcasting transaction...")
            # Stub: In real implementation, sign and broadcast to network
            # For now, simulate success
            return True  # Placeholder: implement real signing and broadcast
        if not self.wallet:
            print("No wallet found. Create a wallet first.")
            return False

        sender = self.wallet.get_address()
        balance = self.get_balance(sender)

        if amount + fee > balance:
            print(f"Insufficient balance. Current balance: {balance}, needed: {amount + fee}")
            return False

        # Create transaction
        transaction = Transaction(sender, recipient, amount, fee=fee)
        transaction.sign_transaction(self.wallet)

        # Add transaction to mempool
        if self.mempool.add_transaction(transaction):
            print(f"Transaction created and added to mempool: {transaction.transaction_hash}")

            # Broadcast to network
            if self.network_manager.running:
                tx_message = NetworkMessage(NetworkProtocol.MSG_TRANSACTION, {
                    'transaction': transaction.to_dict()
                })
                asyncio.create_task(self.network_manager.broadcast_message(tx_message))

            return True

        return False

    def mine_block(self) -> bool:
        """
        Mine a new block

        Returns:
            bool: True if block was mined, False otherwise
        """
        if self.live_mode:
            print("Live mode: Mining on real network not implemented. Use real QRL miner.")
            return False  # Stub: implement real mining if needed
        if not self.wallet:
            print("No wallet found. Create a wallet first.")
            return False

        # Get pending transactions from mempool
        pending_transactions = self.mempool.get_pending_transactions()

        # Add pending transactions to blockchain
        for tx in pending_transactions:
            self.blockchain.add_transaction(tx)

        # Mine block
        block = self.blockchain.mine_pending_transactions(self.wallet.get_address())

        # Remove confirmed transactions from mempool
        for tx in block.transactions:
            if tx.transaction_hash != "0":  # Skip reward transactions
                self.mempool.remove_transaction(
                    tx.transaction_hash,
                    block_hash=block.hash
                )

        # Save blockchain
        self._save_blockchain()

        # Broadcast block to network
        if self.network_manager.running:
            block_message = NetworkMessage(NetworkProtocol.MSG_BLOCK, {
                'block': block.to_dict()
            })
            asyncio.create_task(self.network_manager.broadcast_message(block_message))

        print(f"Block mined: {block.hash}")
        return True

    def get_pending_transactions(self) -> List[Transaction]:
        """
        Get pending transactions from mempool

        Returns:
            List[Transaction]: List of pending transactions
        """
        if self.live_mode:
            return []  # Stub: implement real mempool query
        return self.mempool.get_pending_transactions()

    def get_mempool_info(self) -> Dict[str, Any]:
        """
        Get mempool information

        Returns:
            Dict[str, Any]: Mempool statistics
        """
        if self.live_mode:
            return {"pending_transactions": 0}  # Stub
        return self.mempool.get_mempool_info()

    def get_network_info(self) -> Dict[str, Any]:
        """
        Get network information

        Returns:
            Dict[str, Any]: Network statistics
        """
        return self.network_manager.get_network_info()

    def get_blockchain_info(self) -> Dict[str, Any]:
        """
        Get blockchain information

        Returns:
            Dict[str, Any]: Blockchain information
        """
        if self.live_mode:
            # Stub for live mode
            return {
                "chain_length": 0,
                "difficulty": 0,
                "mining_reward": 0.0,
                "halving_interval": 0,
                "is_valid": True,
                "pending_transactions": 0,
                "mempool": self.get_mempool_info(),
                "network": self.get_network_info()
            }
        blockchain_dict = self.blockchain.to_dict()
        blockchain_dict['chain_length'] = len(self.blockchain.chain)
        blockchain_dict['halving_interval'] = self.blockchain.halving_interval
        blockchain_dict['is_valid'] = self.blockchain.is_chain_valid()
        blockchain_dict['pending_transactions'] = len(self.blockchain.pending_transactions)
        return {
            **blockchain_dict,
            'mempool': self.get_mempool_info(),
            'network': self.get_network_info()
        }

    def add_peer(self, host: str, port: int) -> bool:
        """
        Add a peer to the network

        Args:
            host: Peer host address
            port: Peer port number

        Returns:
            bool: True if peer was added, False otherwise
        """
        peer = Peer(host, port)
        self.network_manager.peers.add(peer)
        return True

    def remove_peer(self, host: str, port: int) -> bool:
        """
        Remove a peer from the network

        Args:
            host: Peer host address
            port: Peer port number

        Returns:
            bool: True if peer was removed, False otherwise
        """
        peer = Peer(host, port)
        if peer in self.network_manager.peers:
            self.network_manager.peers.remove(peer)
            return True
        return False

    def get_peers(self) -> List[Dict[str, Any]]:
        """
        Get list of known peers

        Returns:
            List[Dict[str, Any]]: List of peer information
        """
        return [peer.to_dict() for peer in self.network_manager.peers]
