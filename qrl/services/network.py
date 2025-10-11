import asyncio
import json
import os
import socket
import threading
import time
from typing import Dict, List, Optional, Set, Any, Callable
from concurrent.futures import ThreadPoolExecutor
import hashlib
import random

from qrl.core.blockchain import Blockchain
from qrl.core.transaction import Transaction
from qrl.core.block import Block
from qrl.config import NODE_PORT, PEER_DISCOVERY_PORT


class Peer:
    """Represents a network peer"""

    def __init__(self, host: str, port: int, peer_id: Optional[str] = None):
        """
        Initialize a peer

        Args:
            host: Peer IP address or hostname
            port: Peer port number
            peer_id: Unique peer identifier
        """
        self.host = host
        self.port = port
        self.peer_id = peer_id or f"{host}:{port}"
        self.last_seen = time.time()
        self.connected = False
        self.handshake_complete = False

    def __str__(self) -> str:
        return f"Peer({self.host}:{self.port})"

    def __eq__(self, other) -> bool:
        if isinstance(other, Peer):
            return self.peer_id == other.peer_id
        return False

    def __hash__(self) -> int:
        return hash(self.peer_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert peer to dictionary representation"""
        return {
            'host': self.host,
            'port': self.port,
            'peer_id': self.peer_id,
            'last_seen': self.last_seen,
            'connected': self.connected,
            'handshake_complete': self.handshake_complete
        }

    @classmethod
    def from_dict(cls, peer_dict: Dict[str, Any]) -> 'Peer':
        """Create peer from dictionary representation"""
        peer = cls(
            host=peer_dict['host'],
            port=peer_dict['port'],
            peer_id=peer_dict['peer_id']
        )
        peer.last_seen = peer_dict.get('last_seen', time.time())
        peer.connected = peer_dict.get('connected', False)
        peer.handshake_complete = peer_dict.get('handshake_complete', False)
        return peer


class NetworkProtocol:
    """Network protocol constants and message types"""

    # Message types
    MSG_HANDSHAKE = 'handshake'
    MSG_HANDSHAKE_ACK = 'handshake_ack'
    MSG_PING = 'ping'
    MSG_PONG = 'pong'
    MSG_GET_PEERS = 'get_peers'
    MSG_PEERS = 'peers'
    MSG_TRANSACTION = 'transaction'
    MSG_BLOCK = 'block'
    MSG_GET_BLOCKS = 'get_blocks'
    MSG_BLOCKS = 'blocks'
    MSG_GET_BLOCKCHAIN_INFO = 'get_blockchain_info'
    MSG_BLOCKCHAIN_INFO = 'blockchain_info'

    # Protocol version
    PROTOCOL_VERSION = '0.2.0'

    # Message format
    MESSAGE_FORMAT = 'json'

    # Timeouts (seconds)
    HANDSHAKE_TIMEOUT = 10
    PING_TIMEOUT = 5
    BLOCK_PROPAGATION_TIMEOUT = 30
    TRANSACTION_PROPAGATION_TIMEOUT = 10

    # Network limits
    MAX_PEERS = 50
    MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MIN_PEERS_FOR_CONSENSUS = 3


class NetworkMessage:
    """Network message wrapper"""

    def __init__(self, msg_type: str, payload: Dict[str, Any], msg_id: Optional[str] = None):
        """
        Initialize a network message

        Args:
            msg_type: Type of message
            payload: Message payload
            msg_id: Optional message ID
        """
        self.msg_type = msg_type
        self.payload = payload
        self.msg_id = msg_id or self._generate_msg_id()
        self.timestamp = time.time()

    def _generate_msg_id(self) -> str:
        """Generate a unique message ID"""
        return hashlib.sha256(f"{self.msg_type}_{self.timestamp}_{random.randint(0, 1000000)}".encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary representation"""
        return {
            'msg_type': self.msg_type,
            'payload': self.payload,
            'msg_id': self.msg_id,
            'timestamp': self.timestamp,
            'protocol_version': NetworkProtocol.PROTOCOL_VERSION
        }

    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, msg_dict: Dict[str, Any]) -> 'NetworkMessage':
        """Create message from dictionary representation"""
        return cls(
            msg_type=msg_dict['msg_type'],
            payload=msg_dict['payload'],
            msg_id=msg_dict.get('msg_id')
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'NetworkMessage':
        """Create message from JSON string"""
        return cls.from_dict(json.loads(json_str))


class PeerConnection:
    """Handles connection to a specific peer"""

    def __init__(self, peer: Peer, network_manager: 'NetworkManager'):
        """
        Initialize peer connection

        Args:
            peer: Peer to connect to
            network_manager: Network manager instance
        """
        self.peer = peer
        self.network_manager = network_manager
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self.last_ping = 0

    async def connect(self) -> bool:
        """Connect to the peer"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.peer.host, self.peer.port
            )
            self.connected = True
            self.peer.connected = True
            self.peer.last_seen = time.time()
            return True
        except Exception as e:
            print(f"Failed to connect to {self.peer}: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the peer"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.connected = False
        self.peer.connected = False

    async def send_message(self, message: NetworkMessage) -> bool:
        """Send a message to the peer"""
        if not self.connected or not self.writer:
            return False

        try:
            json_data = message.to_json() + '\n'
            self.writer.write(json_data.encode())
            await self.writer.drain()
            return True
        except Exception as e:
            print(f"Failed to send message to {self.peer}: {e}")
            await self.disconnect()
            return False

    async def receive_message(self) -> Optional[NetworkMessage]:
        """Receive a message from the peer"""
        if not self.connected or not self.reader:
            return None

        try:
            data = await self.reader.readline()
            if not data:
                await self.disconnect()
                return None

            json_str = data.decode().strip()
            if not json_str:
                return None

            return NetworkMessage.from_json(json_str)
        except Exception as e:
            print(f"Failed to receive message from {self.peer}: {e}")
            await self.disconnect()
            return None
class NetworkManager:
    """Manages peer connections and network communication"""

    def __init__(self, blockchain: Blockchain, host: str = '0.0.0.0', port: int = NODE_PORT):
        """
        Initialize network manager

        Args:
            blockchain: Blockchain instance
            host: Host address to bind to
            port: Port number to bind to
        """
        self.blockchain = blockchain
        self.host = host
        self.port = port

        # Peer management
        self.peers: Set[Peer] = set()
        self.peer_connections: Dict[str, PeerConnection] = {}
        self.known_peers_file = "known_peers.json"

        # Network state
        self.running = False
        self.server: Optional[asyncio.AbstractServer] = None

        # Message handlers
        self.message_handlers: Dict[str, Callable] = {
            NetworkProtocol.MSG_HANDSHAKE: self._handle_handshake,
            NetworkProtocol.MSG_HANDSHAKE_ACK: self._handle_handshake_ack,
            NetworkProtocol.MSG_PING: self._handle_ping,
            NetworkProtocol.MSG_PONG: self._handle_pong,
            NetworkProtocol.MSG_GET_PEERS: self._handle_get_peers,
            NetworkProtocol.MSG_PEERS: self._handle_peers,
            NetworkProtocol.MSG_TRANSACTION: self._handle_transaction,
            NetworkProtocol.MSG_BLOCK: self._handle_block,
            NetworkProtocol.MSG_GET_BLOCKS: self._handle_get_blocks,
            NetworkProtocol.MSG_BLOCKS: self._handle_blocks,
            NetworkProtocol.MSG_GET_BLOCKCHAIN_INFO: self._handle_get_blockchain_info,
            NetworkProtocol.MSG_BLOCKCHAIN_INFO: self._handle_blockchain_info,
        }

        # Event callbacks
        self.on_peer_connected: Optional[Callable[[Peer], None]] = None
        self.on_peer_disconnected: Optional[Callable[[Peer], None]] = None
        self.on_transaction_received: Optional[Callable[[Transaction], None]] = None
        self.on_block_received: Optional[Callable[[Block], None]] = None

        # Load known peers
        self._load_known_peers()

    def _load_known_peers(self):
        """Load known peers from file"""
        try:
            if os.path.exists(self.known_peers_file):
                with open(self.known_peers_file, 'r') as f:
                    peers_data = json.load(f)
                    for peer_data in peers_data:
                        peer = Peer.from_dict(peer_data)
                        self.peers.add(peer)
        except Exception as e:
            print(f"Error loading known peers: {e}")

    def _save_known_peers(self):
        """Save known peers to file"""
        try:
            peers_data = [peer.to_dict() for peer in self.peers]
            with open(self.known_peers_file, 'w') as f:
                json.dump(peers_data, f, indent=2)
        except Exception as e:
            print(f"Error saving known peers: {e}")

    async def start(self):
        """Start the network manager"""
        self.running = True
        print(f"Starting network manager on {self.host}:{self.port}")

        # Start server
        self.server = await asyncio.start_server(
            self._handle_client_connection, self.host, self.port
        )

        # Start background tasks
        asyncio.create_task(self._peer_discovery_task())
        asyncio.create_task(self._peer_management_task())
        asyncio.create_task(self._ping_task())

        print(f"Network manager started. Listening on {self.host}:{self.port}")

    async def stop(self):
        """Stop the network manager"""
        self.running = False

        # Close all peer connections
        for connection in self.peer_connections.values():
            await connection.disconnect()

        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        # Save known peers
        self._save_known_peers()

        print("Network manager stopped")

    async def connect_to_peer(self, peer: Peer) -> bool:
        """Connect to a specific peer"""
        if peer.peer_id in self.peer_connections:
            return self.peer_connections[peer.peer_id].connected

        connection = PeerConnection(peer, self)
        if await connection.connect():
            self.peer_connections[peer.peer_id] = connection
            await self._send_handshake(connection)

            # Notify callback
            if self.on_peer_connected:
                self.on_peer_connected(peer)

            return True
        return False

    async def disconnect_from_peer(self, peer: Peer):
        """Disconnect from a specific peer"""
        if peer.peer_id in self.peer_connections:
            connection = self.peer_connections[peer.peer_id]
            await connection.disconnect()
            del self.peer_connections[peer.peer_id]

            # Notify callback
            if self.on_peer_disconnected:
                self.on_peer_disconnected(peer)

    async def broadcast_message(self, message: NetworkMessage, exclude_peer: Optional[Peer] = None):
        """Broadcast a message to all connected peers"""
        for peer_id, connection in list(self.peer_connections.items()):
            if connection.connected and (not exclude_peer or connection.peer != exclude_peer):
                await connection.send_message(message)

    async def send_message_to_peer(self, peer: Peer, message: NetworkMessage) -> bool:
        """Send a message to a specific peer"""
        if peer.peer_id in self.peer_connections:
            connection = self.peer_connections[peer.peer_id]
            return await connection.send_message(message)
        return False

    async def _handle_client_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming client connection"""
        peer_host, peer_port = writer.get_extra_info('peername')
        peer = Peer(peer_host, peer_port)
        connection = PeerConnection(peer, self)
        connection.reader = reader
        connection.writer = writer
        connection.connected = True

        print(f"New connection from {peer}")

        try:
            while self.running:
                message = await connection.receive_message()
                if message is None:
                    break

                await self._handle_message(connection, message)

        except Exception as e:
            print(f"Error handling connection from {peer}: {e}")
        finally:
            await connection.disconnect()

    async def _handle_message(self, connection: PeerConnection, message: NetworkMessage):
        """Handle incoming message"""
        if message.msg_type in self.message_handlers:
            await self.message_handlers[message.msg_type](connection, message)
        else:
            print(f"Unknown message type: {message.msg_type}")

    async def _send_handshake(self, connection: PeerConnection):
        """Send handshake message to peer"""
        payload = {
            'node_info': {
                'host': self.host,
                'port': self.port,
                'protocol_version': NetworkProtocol.PROTOCOL_VERSION,
                'blockchain_height': len(self.blockchain.chain)
            }
        }

        handshake_msg = NetworkMessage(NetworkProtocol.MSG_HANDSHAKE, payload)
        await connection.send_message(handshake_msg)

    async def _handle_handshake(self, connection: PeerConnection, message: NetworkMessage):
        """Handle handshake message"""
        payload = message.payload
        node_info = payload.get('node_info', {})

        # Update peer information
        connection.peer.host = node_info.get('host', connection.peer.host)
        connection.peer.port = node_info.get('port', connection.peer.port)

        # Add peer to known peers
        self.peers.add(connection.peer)

        # Send handshake acknowledgment
        ack_payload = {
            'node_info': {
                'host': self.host,
                'port': self.port,
                'protocol_version': NetworkProtocol.PROTOCOL_VERSION,
                'blockchain_height': len(self.blockchain.chain)
            }
        }

        ack_msg = NetworkMessage(NetworkProtocol.MSG_HANDSHAKE_ACK, ack_payload)
        await connection.send_message(ack_msg)

        connection.peer.handshake_complete = True

    async def _handle_handshake_ack(self, connection: PeerConnection, message: NetworkMessage):
        """Handle handshake acknowledgment"""
        payload = message.payload
        node_info = payload.get('node_info', {})

        # Update peer information
        connection.peer.host = node_info.get('host', connection.peer.host)
        connection.peer.port = node_info.get('port', connection.peer.port)

        # Add peer to known peers
        self.peers.add(connection.peer)

        connection.peer.handshake_complete = True

        print(f"Handshake completed with {connection.peer}")

    async def _handle_ping(self, connection: PeerConnection, message: NetworkMessage):
        """Handle ping message"""
        # Send pong response
        pong_msg = NetworkMessage(NetworkProtocol.MSG_PONG, {})
        await connection.send_message(pong_msg)

    async def _handle_pong(self, connection: PeerConnection, message: NetworkMessage):
        """Handle pong message"""
        connection.peer.last_seen = time.time()

    async def _handle_get_peers(self, connection: PeerConnection, message: NetworkMessage):
        """Handle get peers request"""
        # Send known peers to requesting peer
        peers_list = [peer.to_dict() for peer in self.peers if peer != connection.peer]
        peers_msg = NetworkMessage(NetworkProtocol.MSG_PEERS, {'peers': peers_list})
        await connection.send_message(peers_msg)

    async def _handle_peers(self, connection: PeerConnection, message: NetworkMessage):
        """Handle peers message"""
        peers_data = message.payload.get('peers', [])
        for peer_data in peers_data:
            peer = Peer.from_dict(peer_data)
            self.peers.add(peer)

    async def _handle_transaction(self, connection: PeerConnection, message: NetworkMessage):
        """Handle transaction message"""
        tx_data = message.payload.get('transaction', {})
        try:
            transaction = Transaction.from_dict(tx_data)

            # Add transaction to blockchain
            if self.blockchain.add_transaction(transaction):
                print(f"Received transaction from {connection.peer}: {transaction.transaction_hash}")

                # Broadcast to other peers
                await self.broadcast_message(message, exclude_peer=connection.peer)

                # Notify callback
                if self.on_transaction_received:
                    self.on_transaction_received(transaction)

        except Exception as e:
            print(f"Error processing transaction: {e}")

    async def _handle_block(self, connection: PeerConnection, message: NetworkMessage):
        """Handle block message"""
        block_data = message.payload.get('block', {})
        try:
            block = Block.from_dict(block_data)

            # Add block to blockchain
            if self.blockchain.add_block(block):
                print(f"Received block from {connection.peer}: {block.hash}")

                # Broadcast to other peers
                await self.broadcast_message(message, exclude_peer=connection.peer)

                # Notify callback
                if self.on_block_received:
                    self.on_block_received(block)

        except Exception as e:
            print(f"Error processing block: {e}")

    async def _handle_get_blocks(self, connection: PeerConnection, message: NetworkMessage):
        """Handle get blocks request"""
        start_height = message.payload.get('start_height', 0)
        end_height = message.payload.get('end_height', len(self.blockchain.chain))

        blocks = []
        for i in range(start_height, min(end_height, len(self.blockchain.chain))):
            blocks.append(self.blockchain.chain[i].to_dict())

        blocks_msg = NetworkMessage(NetworkProtocol.MSG_BLOCKS, {'blocks': blocks})
        await connection.send_message(blocks_msg)

    async def _handle_blocks(self, connection: PeerConnection, message: NetworkMessage):
        """Handle blocks message"""
        blocks_data = message.payload.get('blocks', [])
        for block_data in blocks_data:
            try:
                block = Block.from_dict(block_data)
                if self.blockchain.add_block(block):
                    print(f"Added block from sync: {block.hash}")
            except Exception as e:
                print(f"Error adding block from sync: {e}")

    async def _handle_get_blockchain_info(self, connection: PeerConnection, message: NetworkMessage):
        """Handle get blockchain info request"""
        info = self.blockchain.to_dict()
        info_msg = NetworkMessage(NetworkProtocol.MSG_BLOCKCHAIN_INFO, {'info': info})
        await connection.send_message(info_msg)

    async def _handle_blockchain_info(self, connection: PeerConnection, message: NetworkMessage):
        """Handle blockchain info message"""
        # Process blockchain info if needed for synchronization
        pass

    async def _peer_discovery_task(self):
        """Background task for peer discovery"""
        while self.running:
            try:
                # Try to discover new peers (simplified implementation)
                # In a real implementation, this would use DNS seeds, IRC, etc.

                # Connect to known peers that aren't connected
                for peer in list(self.peers):
                    if (peer.peer_id not in self.peer_connections or
                        not self.peer_connections[peer.peer_id].connected):
                        if len(self.peer_connections) < NetworkProtocol.MAX_PEERS:
                            await self.connect_to_peer(peer)

                await asyncio.sleep(30)  # Wait 30 seconds before next discovery attempt

            except Exception as e:
                print(f"Error in peer discovery: {e}")
                await asyncio.sleep(10)

    async def _peer_management_task(self):
        """Background task for peer management"""
        while self.running:
            try:
                # Remove dead connections
                current_time = time.time()
                dead_peers = []

                for peer_id, connection in list(self.peer_connections.items()):
                    if (not connection.connected or
                        current_time - connection.peer.last_seen > 300):  # 5 minutes timeout
                        dead_peers.append(peer_id)

                for peer_id in dead_peers:
                    connection = self.peer_connections[peer_id]
                    await connection.disconnect()
                    del self.peer_connections[peer_id]

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                print(f"Error in peer management: {e}")
                await asyncio.sleep(10)

    async def _ping_task(self):
        """Background task for sending pings"""
        while self.running:
            try:
                # Send ping to all connected peers
                for connection in self.peer_connections.values():
                    if connection.connected and connection.peer.handshake_complete:
                        current_time = time.time()
                        if current_time - connection.last_ping > NetworkProtocol.PING_TIMEOUT:
                            ping_msg = NetworkMessage(NetworkProtocol.MSG_PING, {})
                            await connection.send_message(ping_msg)
                            connection.last_ping = current_time

                await asyncio.sleep(NetworkProtocol.PING_TIMEOUT)

            except Exception as e:
                print(f"Error in ping task: {e}")
                await asyncio.sleep(10)

    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        connected_peers = [peer.to_dict() for peer in self.peers if peer.connected]
        return {
            'total_peers': len(self.peers),
            'connected_peers': len(connected_peers),
            'peer_connections': len(self.peer_connections),
            'running': self.running
        }
