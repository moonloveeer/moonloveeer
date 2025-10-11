import time
import heapq
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from qrl.core.transaction import Transaction


class TransactionStatus(Enum):
    """Transaction status in the mempool"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class MempoolTransaction:
    """Transaction with additional metadata for mempool management"""
    transaction: Transaction
    added_time: float
    last_seen: float
    fee_per_byte: float
    size_bytes: int
    status: TransactionStatus = TransactionStatus.PENDING
    confirmed_in_block: Optional[str] = None
    rejection_reason: Optional[str] = None

    def __lt__(self, other: 'MempoolTransaction') -> bool:
        """Priority comparison for heap ordering (higher fee per byte = higher priority)"""
        return self.fee_per_byte > other.fee_per_byte  # Higher fee per byte first

    def __eq__(self, other: 'MempoolTransaction') -> bool:
        return self.transaction.transaction_hash == other.transaction.transaction_hash


class Mempool:
    """Manages pending transactions for the QRL blockchain"""

    def __init__(self, max_size: int = 10000, max_size_bytes: int = 10 * 1024 * 1024):  # 10MB default
        """
        Initialize a new Mempool

        Args:
            max_size: Maximum number of transactions in mempool
            max_size_bytes: Maximum size of mempool in bytes
        """
        self.max_size = max_size
        self.max_size_bytes = max_size_bytes

        # Main storage structures
        self.transactions: Dict[str, MempoolTransaction] = {}  # tx_hash -> MempoolTransaction
        self.priority_queue: List[MempoolTransaction] = []  # Min-heap for fee-based prioritization
        self.orphaned_transactions: Set[str] = set()  # Transaction hashes that depend on missing transactions

        # Statistics and limits
        self.total_size_bytes = 0
        self.total_fee = 0.0
        self.transaction_count = 0

        # Configuration
        self.min_fee_per_byte = 0.00001  # Minimum fee per byte
        self.max_transaction_age = 3600 * 24  # 24 hours in seconds
        self.min_transaction_size = 100  # Minimum transaction size in bytes
        self.max_transaction_size = 1024 * 1024  # 1MB maximum transaction size

        # Recent transactions cache for duplicate detection
        self.recent_transactions: Set[str] = set()
        self.recent_transactions_max_size = 1000

    def add_transaction(self, transaction: Transaction, peer_id: Optional[str] = None) -> bool:
        """
        Add a transaction to the mempool

        Args:
            transaction: Transaction to add
            peer_id: ID of the peer that sent the transaction

        Returns:
            bool: True if transaction was added, False otherwise
        """
        tx_hash = transaction.transaction_hash

        # Check if transaction already exists
        if tx_hash in self.transactions:
            # Update last_seen time
            self.transactions[tx_hash].last_seen = time.time()
            return True

        # Validate transaction
        if not self._validate_transaction(transaction):
            return False

        # Check size limits
        tx_size = self._calculate_transaction_size(transaction)
        if tx_size > self.max_transaction_size:
            print(f"Transaction too large: {tx_size} bytes")
            return False

        if self.total_size_bytes + tx_size > self.max_size_bytes:
            # Try to evict some transactions to make room
            if not self._evict_transactions_for_space(tx_size):
                print("Mempool full, cannot add transaction")
                return False

        if self.transaction_count >= self.max_size:
            # Try to evict lowest priority transactions
            if not self._evict_transactions_for_space(0):
                print("Mempool full, cannot add transaction")
                return False

        # Calculate fee per byte
        fee_per_byte = transaction.fee / max(tx_size, 1)

        # Create mempool transaction
        mempool_tx = MempoolTransaction(
            transaction=transaction,
            added_time=time.time(),
            last_seen=time.time(),
            fee_per_byte=fee_per_byte,
            size_bytes=tx_size
        )

        # Add to storage
        self.transactions[tx_hash] = mempool_tx
        heapq.heappush(self.priority_queue, mempool_tx)

        # Update statistics
        self.total_size_bytes += tx_size
        self.total_fee += transaction.fee
        self.transaction_count += 1

        # Add to recent transactions cache
        self.recent_transactions.add(tx_hash)
        if len(self.recent_transactions) > self.recent_transactions_max_size:
            # Remove oldest transaction from cache (simple FIFO)
            oldest_tx = next(iter(self.recent_transactions))
            self.recent_transactions.remove(oldest_tx)

        print(f"Added transaction to mempool: {tx_hash}, fee: {transaction.fee}, size: {tx_size} bytes")
        return True

    def remove_transaction(self, tx_hash: str, status: TransactionStatus = TransactionStatus.CONFIRMED,
                          block_hash: Optional[str] = None, reason: Optional[str] = None) -> bool:
        """
        Remove a transaction from the mempool

        Args:
            tx_hash: Transaction hash to remove
            status: New status for the transaction
            block_hash: Hash of block that confirmed the transaction
            reason: Reason for rejection/expiration

        Returns:
            bool: True if transaction was removed, False otherwise
        """
        if tx_hash not in self.transactions:
            return False

        mempool_tx = self.transactions[tx_hash]

        # Update transaction status
        mempool_tx.status = status
        if block_hash:
            mempool_tx.confirmed_in_block = block_hash
        if reason:
            mempool_tx.rejection_reason = reason

        # Remove from storage
        del self.transactions[tx_hash]

        # Remove from priority queue (inefficient but simple for now)
        self.priority_queue = [tx for tx in self.priority_queue if tx.transaction.transaction_hash != tx_hash]
        heapq.heapify(self.priority_queue)

        # Update statistics
        self.total_size_bytes -= mempool_tx.size_bytes
        self.total_fee -= mempool_tx.transaction.fee
        self.transaction_count -= 1

        # Remove from recent transactions cache
        self.recent_transactions.discard(tx_hash)

        return True

    def get_pending_transactions(self, max_count: Optional[int] = None) -> List[Transaction]:
        """
        Get pending transactions sorted by priority

        Args:
            max_count: Maximum number of transactions to return

        Returns:
            List[Transaction]: List of pending transactions
        """
        # Remove expired transactions first
        self._remove_expired_transactions()

        transactions = [mempool_tx.transaction for mempool_tx in self.transactions.values()
                       if mempool_tx.status == TransactionStatus.PENDING]

        # Sort by priority (fee per byte)
        transactions.sort(key=lambda tx: tx.fee / max(self._calculate_transaction_size(tx), 1), reverse=True)

        if max_count:
            transactions = transactions[:max_count]

        return transactions

    def get_transaction(self, tx_hash: str) -> Optional[Transaction]:
        """
        Get a transaction by hash

        Args:
            tx_hash: Transaction hash

        Returns:
            Optional[Transaction]: Transaction if found, None otherwise
        """
        if tx_hash in self.transactions:
            return self.transactions[tx_hash].transaction
        return None

    def is_transaction_pending(self, tx_hash: str) -> bool:
        """
        Check if a transaction is pending in the mempool

        Args:
            tx_hash: Transaction hash

        Returns:
            bool: True if transaction is pending
        """
        return (tx_hash in self.transactions and
                self.transactions[tx_hash].status == TransactionStatus.PENDING)

    def _validate_transaction(self, transaction: Transaction) -> bool:
        """
        Validate a transaction before adding to mempool

        Args:
            transaction: Transaction to validate

        Returns:
            bool: True if valid, False otherwise
        """
        # Check if transaction is valid
        if not transaction.is_valid():
            return False

        # Check minimum fee per byte
        tx_size = self._calculate_transaction_size(transaction)
        fee_per_byte = transaction.fee / max(tx_size, 1)

        if fee_per_byte < self.min_fee_per_byte:
            print(f"Transaction fee too low: {fee_per_byte} < {self.min_fee_per_byte}")
            return False

        # Check if transaction already in recent cache (duplicate detection)
        if transaction.transaction_hash in self.recent_transactions:
            print("Transaction already seen recently")
            return False

        return True

    def _calculate_transaction_size(self, transaction: Transaction) -> int:
        """
        Calculate the size of a transaction in bytes

        Args:
            transaction: Transaction to calculate size for

        Returns:
            int: Size in bytes
        """
        # Simple size calculation - in reality this would be more sophisticated
        tx_dict = transaction.to_dict()
        return len(str(tx_dict).encode('utf-8'))

    def _evict_transactions_for_space(self, required_space: int) -> bool:
        """
        Evict low-priority transactions to make space

        Args:
            required_space: Space needed in bytes

        Returns:
            bool: True if enough space was freed, False otherwise
        """
        initial_count = len(self.priority_queue)
        target_size = self.max_size_bytes - required_space

        while self.total_size_bytes > target_size and self.priority_queue:
            # Remove lowest priority transaction
            lowest_priority_tx = heapq.heappop(self.priority_queue)

            if lowest_priority_tx.transaction.transaction_hash in self.transactions:
                self.remove_transaction(
                    lowest_priority_tx.transaction.transaction_hash,
                    TransactionStatus.REJECTED,
                    reason="Evicted due to mempool size limits"
                )

        return self.total_size_bytes <= target_size

    def _remove_expired_transactions(self):
        """
        Remove expired transactions from the mempool
        """
        current_time = time.time()
        expired_hashes = []

        for tx_hash, mempool_tx in self.transactions.items():
            if (current_time - mempool_tx.added_time > self.max_transaction_age and
                mempool_tx.status == TransactionStatus.PENDING):
                expired_hashes.append(tx_hash)

        for tx_hash in expired_hashes:
            self.remove_transaction(
                tx_hash,
                TransactionStatus.EXPIRED,
                reason=f"Transaction expired after {self.max_transaction_age} seconds"
            )

    def get_mempool_info(self) -> Dict[str, Any]:
        """
        Get mempool information and statistics

        Returns:
            Dict[str, Any]: Mempool statistics
        """
        pending_count = sum(1 for tx in self.transactions.values()
                          if tx.status == TransactionStatus.PENDING)

        return {
            'total_transactions': len(self.transactions),
            'pending_transactions': pending_count,
            'total_size_bytes': self.total_size_bytes,
            'total_fee': self.total_fee,
            'max_size': self.max_size,
            'max_size_bytes': self.max_size_bytes,
            'min_fee_per_byte': self.min_fee_per_byte,
            'average_fee_per_byte': self.total_fee / max(self.total_size_bytes, 1),
            'oldest_transaction_age': self._get_oldest_transaction_age()
        }

    def _get_oldest_transaction_age(self) -> float:
        """
        Get the age of the oldest pending transaction

        Returns:
            float: Age in seconds, or 0 if no pending transactions
        """
        if not self.transactions:
            return 0.0

        current_time = time.time()
        oldest_age = 0.0

        for mempool_tx in self.transactions.values():
            if mempool_tx.status == TransactionStatus.PENDING:
                age = current_time - mempool_tx.added_time
                oldest_age = max(oldest_age, age)

        return oldest_age

    def clear(self):
        """Clear all transactions from the mempool"""
        self.transactions.clear()
        self.priority_queue.clear()
        self.orphaned_transactions.clear()
        self.total_size_bytes = 0
        self.total_fee = 0.0
        self.transaction_count = 0
        self.recent_transactions.clear()

    def get_transactions_by_fee_range(self, min_fee: float, max_fee: Optional[float] = None) -> List[Transaction]:
        """
        Get transactions within a fee range

        Args:
            min_fee: Minimum fee
            max_fee: Maximum fee (optional)

        Returns:
            List[Transaction]: List of transactions in the fee range
        """
        transactions = []

        for mempool_tx in self.transactions.values():
            if mempool_tx.status == TransactionStatus.PENDING:
                if min_fee <= mempool_tx.transaction.fee:
                    if max_fee is None or mempool_tx.transaction.fee <= max_fee:
                        transactions.append(mempool_tx.transaction)

        return transactions

    def get_high_priority_transactions(self, min_fee_per_byte: float) -> List[Transaction]:
        """
        Get high priority transactions above a fee per byte threshold

        Args:
            min_fee_per_byte: Minimum fee per byte threshold

        Returns:
            List[Transaction]: List of high priority transactions
        """
        transactions = []

        for mempool_tx in self.transactions.values():
            if (mempool_tx.status == TransactionStatus.PENDING and
                mempool_tx.fee_per_byte >= min_fee_per_byte):
                transactions.append(mempool_tx.transaction)

        # Sort by priority
        transactions.sort(key=lambda tx: tx.fee / max(self._calculate_transaction_size(tx), 1), reverse=True)
        return transactions

    def update_transaction_status(self, tx_hash: str, status: TransactionStatus,
                                block_hash: Optional[str] = None, reason: Optional[str] = None):
        """
        Update the status of a transaction

        Args:
            tx_hash: Transaction hash
            status: New status
            block_hash: Hash of block that confirmed the transaction
            reason: Reason for status change
        """
        if tx_hash in self.transactions:
            mempool_tx = self.transactions[tx_hash]
            mempool_tx.status = status

    def get_transaction_by_hash_prefix(self, hash_prefix: str) -> Optional[Transaction]:
        """
        Get a transaction by hash prefix (for search functionality)

        Args:
            hash_prefix: Transaction hash prefix to search for

        Returns:
            Optional[Transaction]: Transaction if found, None otherwise
        """
        for mempool_tx in self.transactions.values():
            if mempool_tx.status == TransactionStatus.PENDING:
                if mempool_tx.transaction.transaction_hash.startswith(hash_prefix):
                    return mempool_tx.transaction
        return None
