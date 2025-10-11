#!/usr/bin/env python

"""
Test script for QRL blockchain

This script demonstrates the basic functionality of the QRL blockchain:
1. Creating wallets with quantum-safe XMSS signatures
2. Creating and signing transactions
3. Mining blocks with Proof-of-Work
4. Verifying the blockchain
"""

import time

from qrl.core.blockchain import Blockchain
from qrl.core.transaction import Transaction
from qrl.crypto.xmss import XMSS


def main():
    print("QRL Blockchain Test")
    print("-" * 50)
    
    # Create blockchain with difficulty 4
    print("Creating blockchain...")
    blockchain = Blockchain(difficulty=4)
    print(f"Blockchain created with difficulty {blockchain.difficulty}")
    print(f"Mining reward: {blockchain.mining_reward} QRL")
    print()
    
    # Create wallets
    print("Creating wallets...")
    alice_wallet = XMSS(height=4)  # 2^4 = 16 signatures
    bob_wallet = XMSS(height=4)
    miner_wallet = XMSS(height=4)
    
    print(f"Alice's address: {alice_wallet.get_address()}")
    print(f"Bob's address: {bob_wallet.get_address()}")
    print(f"Miner's address: {miner_wallet.get_address()}")
    print()
    
    # Mine first block to get some coins
    print("Mining first block...")
    start_time = time.time()
    blockchain.mine_pending_transactions(miner_wallet.get_address())
    end_time = time.time()
    print(f"Block mined in {end_time - start_time:.2f} seconds")
    print(f"Miner's balance: {blockchain.get_balance(miner_wallet.get_address())} QRL")
    print()
    
    # Create a transaction
    print("Creating transaction from miner to Alice...")
    tx1 = Transaction(miner_wallet.get_address(), alice_wallet.get_address(), 50.0)
    tx1.sign_transaction(miner_wallet)
    blockchain.add_transaction(tx1)
    print(f"Transaction created: {tx1.transaction_hash}")
    print()
    
    # Mine second block
    print("Mining second block...")
    start_time = time.time()
    blockchain.mine_pending_transactions(miner_wallet.get_address())
    end_time = time.time()
    print(f"Block mined in {end_time - start_time:.2f} seconds")
    print()
    
    # Check balances
    print("Checking balances...")
    print(f"Miner's balance: {blockchain.get_balance(miner_wallet.get_address())} QRL")
    print(f"Alice's balance: {blockchain.get_balance(alice_wallet.get_address())} QRL")
    print(f"Bob's balance: {blockchain.get_balance(bob_wallet.get_address())} QRL")
    print()
    
    # Create another transaction
    print("Creating transaction from Alice to Bob...")
    tx2 = Transaction(alice_wallet.get_address(), bob_wallet.get_address(), 25.0)
    tx2.sign_transaction(alice_wallet)
    blockchain.add_transaction(tx2)
    print(f"Transaction created: {tx2.transaction_hash}")
    print()
    
    # Mine third block
    print("Mining third block...")
    start_time = time.time()
    blockchain.mine_pending_transactions(miner_wallet.get_address())
    end_time = time.time()
    print(f"Block mined in {end_time - start_time:.2f} seconds")
    print()
    
    # Check final balances
    print("Checking final balances...")
    print(f"Miner's balance: {blockchain.get_balance(miner_wallet.get_address())} QRL")
    print(f"Alice's balance: {blockchain.get_balance(alice_wallet.get_address())} QRL")
    print(f"Bob's balance: {blockchain.get_balance(bob_wallet.get_address())} QRL")
    print()
    
    # Verify blockchain
    print("Verifying blockchain...")
    print(f"Blockchain valid: {blockchain.is_chain_valid()}")
    print()
    
    # Print blockchain info
    print("Blockchain info:")
    print(f"Chain length: {len(blockchain.chain)}")
    print(f"Genesis block hash: {blockchain.chain[0].hash}")
    print(f"Latest block hash: {blockchain.get_latest_block().hash}")
    print()
    
    print("Test completed successfully!")


if __name__ == "__main__":
    main()