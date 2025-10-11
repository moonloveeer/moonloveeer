import time
import hashlib
import json
from typing import Dict, Any, Optional

from qrl.crypto.xmss import XMSS


class Transaction:
    """Transaction class for the QRL blockchain"""
    
    def __init__(self, sender: str, recipient: str, amount: float,
                 signature: Optional[str] = None, timestamp: Optional[float] = None,
                 fee: float = 0.0):
        """
        Initialize a new Transaction

        Args:
            sender: Sender's address
            recipient: Recipient's address
            amount: Amount to transfer
            signature: XMSS signature of the transaction
            timestamp: Transaction creation timestamp
            fee: Transaction fee in coins (optional, defaults to 0)
        """
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.fee = fee
        self.timestamp = timestamp or time.time()
        self.signature = signature
        self.transaction_hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """
        Calculate the hash of the transaction using SHA-256

        Returns:
            str: Hexadecimal string representation of the transaction hash
        """
        tx_string = json.dumps({
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp
        }, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()
    
    def sign_transaction(self, xmss: XMSS) -> None:
        """
        Sign the transaction using XMSS
        
        Args:
            xmss: XMSS instance for signing
        """
        if xmss.get_address() != self.sender:
            raise ValueError("You cannot sign transactions for other wallets")
        
        self.signature = xmss.sign(self.transaction_hash.encode())
    
    def is_coinbase(self) -> bool:
        """
        Return True if this is a coinbase (mining reward) transaction.
        Coinbase transactions are created by the system with sender "0".
        """
        return self.sender == "0"

    def is_valid(self) -> bool:
        """
        Validate the transaction
        
        Returns:
            bool: True if transaction is valid, False otherwise
        """
        # Special rules for coinbase (mining reward) transactions
        # These are created by the system and do not require a signature.
        if self.is_coinbase():
            # Must have a positive amount, zero fee, and no signature
            if self.amount <= 0:
                return False
            if self.fee != 0:
                return False
            # Signature should be absent for coinbase
            if self.signature not in (None, ""):
                return False
            return True

        # Check if amount is positive
        if self.amount <= 0:
            return False

        # Check if fee is non-negative
        if self.fee < 0:
            return False

        # Check if sender and recipient are different
        if self.sender == self.recipient:
            return False

        # Check if signature exists
        if not self.signature:
            return False

        return True

    def get_total_amount(self) -> float:
        """
        Get the total amount that will be deducted from sender's balance

        Returns:
            float: Total amount (transaction amount + fee)
        """
        return self.amount + self.fee

    def get_fee_percentage(self) -> float:
        """
        Calculate the fee as a percentage of the transaction amount

        Returns:
            float: Fee percentage
        """
        if self.amount <= 0:
            return 0.0
        return (self.fee / self.amount) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the transaction to a dictionary representation

        Returns:
            Dict[str, Any]: Dictionary representation of the transaction
        """
        return {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp,
            'signature': self.signature,
            'transaction_hash': self.transaction_hash
        }
    
    @classmethod
    def from_dict(cls, tx_dict: Dict[str, Any]) -> 'Transaction':
        """
        Create a Transaction instance from a dictionary

        Args:
            tx_dict: Dictionary representation of a transaction

        Returns:
            Transaction: A new Transaction instance
        """
        tx = cls(
            sender=tx_dict['sender'],
            recipient=tx_dict['recipient'],
            amount=tx_dict['amount'],
            fee=tx_dict.get('fee', 0.0),  # Default to 0.0 if fee not present (backward compatibility)
            signature=tx_dict.get('signature'),
            timestamp=tx_dict['timestamp']
        )
        tx.transaction_hash = tx_dict.get('transaction_hash', tx.calculate_hash())
        return tx