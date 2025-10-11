import click

from qrl.services.node_service import NodeService


@click.group()
def cli():
    """QRL - Quantum Resistant Ledger CLI"""
    pass


@cli.command('wallet_gen')
@click.option('--height', default=10, help='Merkle tree height')
def wallet_gen(height):
    """Generate a new wallet"""
    node = NodeService()
    address = node.create_wallet(height=height)
    click.echo(f"Wallet created with address: {address}")


@cli.command('wallet_info')
def wallet_info():
    """Get wallet information"""
    node = NodeService()
    address = node.get_wallet_address()
    
    if not address:
        click.echo("No wallet found. Create a wallet first.")
        return
    
    balance = node.get_balance(address)
    click.echo(f"Wallet address: {address}")
    click.echo(f"Balance: {balance}")


@cli.command('tx_transfer')
@click.option('--dst', required=True, help='Destination address')
@click.option('--amount', required=True, type=float, help='Amount to transfer')
def tx_transfer(dst, amount):
    """Create a new transaction"""
    node = NodeService()
    result = node.create_transaction(dst, amount)
    
    if result:
        click.echo(f"Transaction created: {amount} QRL sent to {dst}")
    else:
        click.echo("Failed to create transaction")


@cli.command('mining_start')
def mining_start():
    """Start mining blocks"""
    node = NodeService()
    result = node.mine_block()
    
    if result:
        click.echo("Block mined successfully")
    else:
        click.echo("Failed to mine block")


@cli.command('blockchain_info')
def blockchain_info():
    """Get blockchain information"""
    node = NodeService()
    info = node.get_blockchain_info()
    
    click.echo("Blockchain Information:")
    click.echo(f"Chain length: {info['chain_length']}")
    click.echo(f"Difficulty: {info['difficulty']}")
    click.echo(f"Initial mining reward: {info['initial_mining_reward']}")
    click.echo(f"Current mining reward: {info['mining_reward']}")
    click.echo(f"Halving interval: {info['halving_interval']} blocks")
    
    # Calculate next halving
    current_height = info['chain_length'] - 1  # Subtract 1 for genesis block
    next_halving = ((current_height // info['halving_interval']) + 1) * info['halving_interval']
    blocks_until_halving = next_halving - current_height
    
    click.echo(f"Next halving at block: {next_halving}")
    click.echo(f"Blocks until next halving: {blocks_until_halving}")
    click.echo(f"Pending transactions: {info['pending_transactions']}")
    click.echo(f"Chain valid: {info['is_valid']}")


def main():
    cli()


if __name__ == '__main__':
    main()