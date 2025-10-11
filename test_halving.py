#!/usr/bin/env python3

import os
import sys
import shutil
from qrl.services.node_service import NodeService
from qrl.crypto.xmss import XMSS

# Function to create a wallet and return its address
def create_wallet(node_service, height=10):
    wallet = XMSS(height=height)
    address = wallet.get_address()
    print(f"Created wallet with address: {address}")
    return wallet, address

# Main function to demonstrate halving mechanism
def main():
    print("QRL Mining Reward Halving Test")
    print("-" * 50)
    
    # Create a node service with a smaller halving interval for testing
    # Use isolated data directory for deterministic runs
    test_data_dir = os.path.join(os.path.dirname(__file__), '.qrl_test')
    if os.path.exists(test_data_dir):
        shutil.rmtree(test_data_dir)
    node_service = NodeService(data_dir=test_data_dir)
    
    # Modify the halving interval for testing purposes
    # In a real implementation, this would be much larger (e.g., 210,000 blocks like Bitcoin)
    node_service.blockchain.halving_interval = 5  # Halve every 5 blocks for testing
    
    # Create a wallet
    print("\nCreating wallet...")
    wallet, address = create_wallet(node_service)
    
    # Set the wallet in the node service
    node_service.wallet = wallet
    node_service._save_wallet()
    
    # Mine blocks and observe the halving
    print("\nMining blocks to observe halving mechanism...")
    
    # Mine 20 blocks to see multiple halvings
    for i in range(20):
        # Get current mining reward before mining
        current_reward = node_service.blockchain.mining_reward
        
        # Mine a block
        result = node_service.mine_block()
        
        # Calculate block height
        block_height = len(node_service.blockchain.chain) - 1  # Subtract 1 for genesis block
        
        # Calculate expected halvings
        halvings = block_height // node_service.blockchain.halving_interval
        
        # Print information
        print(f"Block {block_height} mined | Reward: {current_reward:.8f} QRL | Halvings: {halvings}")
    
    # Check final balance
    balance = node_service.get_balance(address)
    print(f"\nFinal wallet balance: {balance:.8f} QRL")
    
    # Verify blockchain
    blockchain_info = node_service.get_blockchain_info()
    print(f"\nBlockchain information:")
    print(f"Chain length: {blockchain_info['chain_length']}")
    print(f"Chain valid: {blockchain_info['is_valid']}")
    
    print("\nHalving test completed successfully!")

if __name__ == "__main__":
    main()