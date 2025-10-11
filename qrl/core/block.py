import time
import hashlib
import json
from typing import List, Dict, Any, Optional

from qrl.core.transaction import Transaction
from qrl.crypto.merkle_tree import MerkleTree


class Block:
    """Block class for the QRL blockchain"""

    def __init__(self, index: int, timestamp: float, transactions: List[Transaction],
                 previous_hash: str, nonce: int = 0):
        """
        Initialize a new Block

        Args:
            index: Block height/index in the chain
            timestamp: Block creation timestamp
            transactions: List of transactions included in the block
            previous_hash: Hash of the previous block
            nonce: Nonce used for mining (Proof of Work)
        """
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce

        # Build Merkle tree for transactions
        self.merkle_tree = MerkleTree([tx.transaction_hash for tx in transactions])
        self.merkle_root = self.merkle_tree.get_root_hash()

        # Calculate hash after all attributes are set
        self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """
        Calculate the hash of the block using SHA-256

        Returns:
            str: Hexadecimal string representation of the block hash
        """
        # Don't include hash in hash calculation to avoid circular reference
        block_dict = {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'merkle_root': self.merkle_root,
            'nonce': self.nonce
        }
        block_string = json.dumps(block_dict, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the block to a dictionary representation

        Returns:
            Dict[str, Any]: Dictionary representation of the block
        """
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'merkle_root': self.merkle_root,
            'nonce': self.nonce,
            'hash': self.hash
        }

    @classmethod
    def from_dict(cls, block_dict: Dict[str, Any]) -> 'Block':
        """
        Create a Block instance from a dictionary

        Args:
            block_dict: Dictionary representation of a block

        Returns:
            Block: A new Block instance
        """
        transactions = [Transaction.from_dict(tx) for tx in block_dict['transactions']]
        block = cls(
            index=block_dict['index'],
            timestamp=block_dict['timestamp'],
            transactions=transactions,
            previous_hash=block_dict['previous_hash'],
            nonce=block_dict['nonce']
        )
        # Set merkle root and hash from stored values
        block.merkle_root = block_dict.get('merkle_root', block.merkle_tree.get_root_hash())
        block.hash = block_dict.get('hash', block._calculate_hash())
        return block

    @classmethod
    def create_genesis_block(cls) -> 'Block':
        """
        Create the genesis block (first block in the chain)

        Returns:
            Block: The genesis block
        """
        return cls(0, time.time(), [], "0", 0)

    def mine_block(self, difficulty: int) -> None:
        """
        Mine the block by finding a hash with the required difficulty

        Args:
            difficulty: The mining difficulty (number of leading zeros required)
        """
        target = '0' * difficulty

        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self._calculate_hash()

    def verify_transaction_inclusion(self, transaction: Transaction) -> bool:
        """
        Verify that a transaction is included in this block using Merkle proof

        Args:
            transaction: Transaction to verify

        Returns:
            bool: True if transaction is included in the block
        """
        if not self.merkle_tree:
            return False

        proof = self.merkle_tree.get_proof(transaction.transaction_hash)
        if proof is None:
            return False

        return self.merkle_tree.verify_proof(transaction.transaction_hash, proof, self.merkle_root)

    def get_transaction_proof(self, transaction: Transaction) -> Optional[List[str]]:
        """
        Get the Merkle proof for a transaction

        Args:
            transaction: Transaction to get proof for

        Returns:
            Optional[List[str]]: Merkle proof or None if transaction not found
        """
        if not self.merkle_tree:
            return None

        return self.merkle_tree.get_proof(transaction.transaction_hash)

    def get_merkle_tree_info(self) -> Dict[str, Any]:
        """
        Get information about the Merkle tree

        Returns:
            Dict[str, Any]: Merkle tree information
        """
        if not self.merkle_tree:
            return {'root_hash': None, 'tree_height': 0, 'leaves_count': 0}

        return self.merkle_tree.to_dict()
