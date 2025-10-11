import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from qrl.core.block import Block
from qrl.core.transaction import Transaction
from qrl.config import (
    INITIAL_MINING_REWARD,
    HALVING_INTERVAL,
    HALVING_FACTOR,
    TARGET_BLOCK_TIME,
    DIFFICULTY_ADJUSTMENT_INTERVAL,
    DIFFICULTY_ADJUSTMENT_WINDOW,
    MIN_DIFFICULTY,
    MAX_DIFFICULTY
)


class Blockchain:
    """Blockchain class for the QRL blockchain"""
    
    def __init__(self, difficulty: int = 4):
        """
        Initialize a new Blockchain
        
        Args:
            difficulty: Initial mining difficulty (number of leading zeros required in block hash)
        """
        self.chain: List[Block] = [Block.create_genesis_block()]
        self.pending_transactions: List[Transaction] = []
        self.difficulty = difficulty
        self.initial_mining_reward = INITIAL_MINING_REWARD
        self.mining_reward = self.initial_mining_reward
        self.halving_interval = HALVING_INTERVAL  # Bitcoin halves every 210,000 blocks
        self.halving_factor = HALVING_FACTOR  # Reduce reward by half
        self.target_block_time = TARGET_BLOCK_TIME  # Target time between blocks in seconds
        self.difficulty_adjustment_interval = DIFFICULTY_ADJUSTMENT_INTERVAL  # Blocks between difficulty adjustments
        self.difficulty_adjustment_window = DIFFICULTY_ADJUSTMENT_WINDOW  # Number of blocks to consider for difficulty adjustment
        self.min_difficulty = MIN_DIFFICULTY  # Minimum difficulty level
        self.max_difficulty = MAX_DIFFICULTY  # Maximum difficulty level
    
    def get_latest_block(self) -> Block:
        """
        Get the latest block in the chain
        
        Returns:
            Block: The latest block
        """
        return self.chain[-1]
    
    def mine_pending_transactions(self, miner_address: str) -> Block:
        """
        Mine pending transactions and add a new block to the chain
        
        Args:
            miner_address: Address to receive mining reward
            
        Returns:
            Block: The newly mined block
        """
        # Calculate current block height
        current_height = len(self.chain)
        
        # Check if we need to halve the mining reward
        if current_height > 0 and self.halving_interval > 0:
            halvings = current_height // self.halving_interval
            if halvings > 0:
                # Calculate the new mining reward based on halvings
                self.mining_reward = self.initial_mining_reward * (self.halving_factor ** halvings)
                # Ensure reward doesn't go below a minimum threshold
                if self.mining_reward < 0.00000001:  # 1 satoshi equivalent
                    self.mining_reward = 0.00000001
        
        # Calculate total fees from pending transactions
        total_fees = sum(tx.fee for tx in self.pending_transactions)

        # Create mining reward transaction (includes base reward + fees)
        total_reward = self.mining_reward + total_fees
        reward_tx = Transaction(
            sender="0",  # "0" represents the system
            recipient=miner_address,
            amount=total_reward,
            fee=0.0  # System transactions don't pay fees
        )
        
        # Add transactions to mine
        transactions_to_mine = self.pending_transactions + [reward_tx]
        
        # Create new block
        block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            transactions=transactions_to_mine,
            previous_hash=self.get_latest_block().hash
        )
        
        # Mine the block
        block.mine_block(self.difficulty)
        
        # Add block to chain
        self.chain.append(block)
        
        # Clear pending transactions
        self.pending_transactions = []
        
        return block
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """
        Add a transaction to pending transactions

        Args:
            transaction: Transaction to add

        Returns:
            bool: True if transaction was added, False otherwise
        """
        # Verify transaction
        if not transaction.is_valid():
            return False

        # Add transaction to pending transactions
        self.pending_transactions.append(transaction)
        return True
    
    def add_block(self, block: Block) -> bool:
        """
        Add a new block to the blockchain
        
        Args:
            block: Block to add
            
        Returns:
            bool: True if block was added, False otherwise
        """
        # Verify block hash meets difficulty requirement
        if not block.hash.startswith('0' * self.difficulty):
            return False
            
        # Verify block index is correct
        if block.index != len(self.chain):
            return False
            
        # Verify previous hash is correct
        if block.index > 0 and block.previous_hash != self.get_latest_block().hash:
            return False
            
        # Verify block hash is valid
        if block.hash != block.calculate_hash():
            return False
            
        # Verify transactions in the block
        for tx in block.transactions:
            if not tx.is_valid():
                return False
        
        # Add block to chain
        self.chain.append(block)
        
        # Adjust difficulty if needed
        if len(self.chain) % self.difficulty_adjustment_interval == 0:
            self.adjust_difficulty()
            
        return True
        
    def get_balance(self, address: str) -> float:
        """
        Get the balance of an address

        Args:
            address: Address to get balance for

        Returns:
            float: Balance of the address
        """
        balance = 0.0

        # Helper: case-insensitive compare for EVM addresses
        def is_eth(addr: str) -> bool:
            return isinstance(addr, str) and addr.lower().startswith('0x') and len(addr) == 42 \
                and all(c in '0123456789abcdef' for c in addr[2:].lower())

        def addr_eq(a: str, b: str) -> bool:
            if is_eth(a) and is_eth(b):
                return a.lower() == b.lower()
            return a == b

        # Check all blocks in the chain
        for block in self.chain:
            for tx in block.transactions:
                if addr_eq(tx.sender, address):
                    balance -= tx.get_total_amount()  # Subtract amount + fee
                if addr_eq(tx.recipient, address):
                    balance += tx.amount  # Add only the amount (fee goes to miner)

        return balance
    
    def is_chain_valid(self) -> bool:
        """
        Validate the blockchain
        
        Returns:
            bool: True if chain is valid, False otherwise
        """
        # Check each block in the chain
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Validate block hash
            if current_block.hash != current_block._calculate_hash():
                return False
            
            # Validate previous hash reference
            if current_block.previous_hash != previous_block.hash:
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the blockchain to a dictionary representation
        
        Returns:
            Dict[str, Any]: Dictionary representation of the blockchain
        """
        return {
            'chain': [block.to_dict() for block in self.chain],
            'pending_transactions': [tx.to_dict() for tx in self.pending_transactions],
            'difficulty': self.difficulty,
            'mining_reward': self.mining_reward
        }
    
    @classmethod
    def from_dict(cls, blockchain_dict: Dict[str, Any]) -> 'Blockchain':
        """
        Create a Blockchain instance from a dictionary
        
        Args:
            blockchain_dict: Dictionary representation of a blockchain
            
        Returns:
            Blockchain: A new Blockchain instance
        """
        blockchain = cls(difficulty=blockchain_dict['difficulty'])
        blockchain.mining_reward = blockchain_dict['mining_reward']
        
        # Load chain
        blockchain.chain = [Block.from_dict(block_dict) for block_dict in blockchain_dict['chain']]
        
        # Load pending transactions
        blockchain.pending_transactions = [Transaction.from_dict(tx_dict) for tx_dict in blockchain_dict['pending_transactions']]
        
        return blockchain