import os
import sys
import time
import logging
import argparse

from qrl.services.node_service import NodeService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('qrl')


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='QRL - Quantum Resistant Ledger')
    parser.add_argument('--data-dir', type=str, default=None,
                        help='Directory to store blockchain data')
    parser.add_argument('--mine', action='store_true',
                        help='Enable automatic mining')
    parser.add_argument('--mine-interval', type=int, default=10,
                        help='Mining interval in seconds')
    
    return parser.parse_args()


def main():
    """Main entry point for the QRL node"""
    args = parse_arguments()
    
    # Initialize node service
    node = NodeService(data_dir=args.data_dir)
    
    # Check if wallet exists, create if not
    if not node.get_wallet_address():
        logger.info("No wallet found. Creating a new wallet...")
        address = node.create_wallet()
        logger.info(f"Wallet created with address: {address}")
    else:
        address = node.get_wallet_address()
        logger.info(f"Using existing wallet with address: {address}")
    
    # Print blockchain info
    info = node.get_blockchain_info()
    logger.info(f"Blockchain initialized with {info['chain_length']} blocks")
    logger.info(f"Mining difficulty: {info['difficulty']}")
    logger.info(f"Mining reward: {info['mining_reward']} QRL")
    
    # Start mining if enabled
    if args.mine:
        logger.info(f"Automatic mining enabled with interval: {args.mine_interval} seconds")
        
        try:
            while True:
                # Mine a block
                logger.info("Mining a new block...")
                result = node.mine_block()
                
                if result:
                    # Get updated balance
                    balance = node.get_balance()
                    logger.info(f"Block mined successfully. Current balance: {balance} QRL")
                else:
                    logger.error("Failed to mine block")
                
                # Wait for next mining interval
                time.sleep(args.mine_interval)
        except KeyboardInterrupt:
            logger.info("Mining stopped by user")
    else:
        logger.info("Node started. Use the CLI to interact with the blockchain.")


if __name__ == '__main__':
    main()