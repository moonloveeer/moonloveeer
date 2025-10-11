#!/usr/bin/env python3

import os
import json
from qrl.services.node_service import NodeService
from qrl.crypto.xmss import XMSS

# Function to create a wallet and return its address
def create_wallet(node_service, height=10):
    wallet = XMSS(height=height)
    address = wallet.get_address()
    print(f"Created wallet with address: {address}")
    return wallet, address

# Main function to demonstrate transaction functionality
def main():
    print("QRL Transaction Test")
    print("-" * 50)
    
    # Create a node service
    node_service = NodeService()
    
    # Create two wallets: sender and receiver
    print("\nCreating sender wallet...")
    sender_wallet, sender_address = create_wallet(node_service)
    
    print("\nCreating receiver wallet...")
    receiver_wallet, receiver_address = create_wallet(node_service)
    
    # Mine some blocks to get coins in the sender wallet
    print("\nMining blocks to get coins in sender wallet...")
    
    # Set the sender wallet in the node service
    node_service.wallet = sender_wallet
    node_service._save_wallet()
    
    # Mine 5 blocks
    for i in range(5):
        result = node_service.mine_block()
        if result:
            print(f"Block {i+1} mined successfully")
    
    # Check balances
    sender_balance = node_service.get_balance(sender_address)
    receiver_balance = node_service.get_balance(receiver_address)
    
    print(f"\nSender balance: {sender_balance} QRL")
    print(f"Receiver balance: {receiver_balance} QRL")
    
    # Send transaction
    amount_to_send = 50.0
    print(f"\nSending {amount_to_send} QRL from sender to receiver...")
    
    result = node_service.create_transaction(receiver_address, amount_to_send)
    if result:
        print("Transaction created successfully")
    else:
        print("Failed to create transaction")
    
    # Mine a block to confirm the transaction
    print("\nMining a block to confirm the transaction...")
    node_service.mine_block()
    
    # Check balances again
    sender_balance = node_service.get_balance(sender_address)
    receiver_balance = node_service.get_balance(receiver_address)
    
    print(f"\nSender balance after transaction: {sender_balance} QRL")
    print(f"Receiver balance after transaction: {receiver_balance} QRL")
    
    # Verify blockchain
    blockchain_info = node_service.get_blockchain_info()
    print(f"\nBlockchain information:")
    print(f"Chain length: {blockchain_info['chain_length']}")
    print(f"Chain valid: {blockchain_info['is_valid']}")
    
    print("\nTransaction test completed successfully!")

if __name__ == "__main__":
    main()