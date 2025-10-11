import hashlib
import json
from typing import List, Optional, Dict, Any, Tuple


class MerkleNode:
    """A node in the Merkle tree"""

    def __init__(self, hash_value: str, left: Optional['MerkleNode'] = None,
                 right: Optional['MerkleNode'] = None, data: Optional[Any] = None):
        """
        Initialize a Merkle node

        Args:
            hash_value: The hash value of this node
            left: Left child node
            right: Right child node
            data: Optional data associated with this node (for leaf nodes)
        """
        self.hash = hash_value
        self.left = left
        self.right = right
        self.data = data

    def is_leaf(self) -> bool:
        """Check if this node is a leaf node"""
        return self.left is None and self.right is None


class MerkleTree:
    """Merkle tree implementation for efficient transaction verification"""

    def __init__(self, data_list: List[Any]):
        """
        Initialize a Merkle tree from a list of data items

        Args:
            data_list: List of data items to build the tree from
        """
        self.leaves: List[MerkleNode] = []
        self.root: Optional[MerkleNode] = None

        # Create leaf nodes
        for data in data_list:
            hash_value = self._hash_data(data)
            leaf = MerkleNode(hash_value, data=data)
            self.leaves.append(leaf)

        # Build the tree
        self.root = self._build_tree(self.leaves)

    def _hash_data(self, data: Any) -> str:
        """
        Hash the given data using SHA-256

        Args:
            data: Data to hash

        Returns:
            str: Hexadecimal hash string
        """
        if isinstance(data, str):
            data_string = data
        else:
            data_string = json.dumps(data, sort_keys=True, default=str)

        return hashlib.sha256(data_string.encode()).hexdigest()

    def _build_tree(self, nodes: List[MerkleNode]) -> Optional[MerkleNode]:
        """
        Recursively build the Merkle tree

        Args:
            nodes: List of nodes at current level

        Returns:
            Optional[MerkleNode]: Root node of the subtree
        """
        if not nodes:
            return None

        if len(nodes) == 1:
            return nodes[0]

        # If odd number of nodes, duplicate the last one
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])

        next_level: List[MerkleNode] = []

        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1]

            # Combine hashes of left and right children
            combined_hash = self._hash_data(left.hash + right.hash)

            parent = MerkleNode(combined_hash, left=left, right=right)
            next_level.append(parent)

        return self._build_tree(next_level)

    def get_root_hash(self) -> Optional[str]:
        """
        Get the root hash of the Merkle tree

        Returns:
            Optional[str]: Root hash or None if tree is empty
        """
        return self.root.hash if self.root else None

    def get_proof(self, data: Any) -> Optional[List[str]]:
        """
        Generate a Merkle proof for the given data

        Args:
            data: Data to generate proof for

        Returns:
            Optional[List[str]]: List of hashes forming the proof, or None if data not found
        """
        target_hash = self._hash_data(data)

        # Find the leaf node containing this data
        target_leaf = None
        for leaf in self.leaves:
            if leaf.hash == target_hash and leaf.data == data:
                target_leaf = leaf
                break

        if not target_leaf:
            return None

        return self._generate_proof(target_leaf, [])

    def _generate_proof(self, node: MerkleNode, proof: List[str]) -> List[str]:
        """
        Recursively generate Merkle proof

        Args:
            node: Current node
            proof: Accumulating proof list

        Returns:
            List[str]: Merkle proof
        """
        if node.is_leaf():
            return proof

        if node.left:
            # If left child exists, add right child's hash to proof and recurse left
            if node.right:
                proof.append(node.right.hash)
            return self._generate_proof(node.left, proof)

        if node.right:
            # If only right child exists, add left child's hash to proof and recurse right
            proof.append(node.left.hash if node.left else "")
            return self._generate_proof(node.right, proof)

        return proof

    def verify_proof(self, data: Any, proof: List[str], root_hash: str) -> bool:
        """
        Verify a Merkle proof

        Args:
            data: Original data
            proof: Merkle proof (list of hashes)
            root_hash: Expected root hash

        Returns:
            bool: True if proof is valid
        """
        if not proof:
            return self._hash_data(data) == root_hash

        computed_hash = self._hash_data(data)

        # Reconstruct the path using the proof
        for proof_hash in proof:
            computed_hash = self._hash_data(computed_hash + proof_hash)

        return computed_hash == root_hash

    def get_tree_height(self) -> int:
        """
        Get the height of the Merkle tree

        Returns:
            int: Height of the tree
        """
        if not self.root:
            return 0

        return self._get_node_height(self.root)

    def _get_node_height(self, node: MerkleNode) -> int:
        """
        Recursively calculate node height

        Args:
            node: Node to calculate height for

        Returns:
            int: Height of the node
        """
        if node.is_leaf():
            return 1

        left_height = self._get_node_height(node.left) if node.left else 0
        right_height = self._get_node_height(node.right) if node.right else 0

        return 1 + max(left_height, right_height)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Merkle tree to a dictionary representation

        Returns:
            Dict[str, Any]: Dictionary representation of the tree
        """
        return {
            'root_hash': self.get_root_hash(),
            'tree_height': self.get_tree_height(),
            'leaves_count': len(self.leaves)
        }

    @classmethod
    def from_dict(cls, tree_dict: Dict[str, Any]) -> 'MerkleTree':
        """
        Create a MerkleTree instance from a dictionary (partial reconstruction)

        Args:
            tree_dict: Dictionary representation of a tree

        Returns:
            MerkleTree: A new MerkleTree instance
        """
        # This is a partial reconstruction - mainly for serialization
        # The actual tree structure is lost, but root hash is preserved
        tree = cls([])
        tree.root = MerkleNode(tree_dict['root_hash'])
        return tree


class MerkleProof:
    """Utility class for handling Merkle proofs"""

    def __init__(self, data: Any, proof: List[str], root_hash: str):
        """
        Initialize a Merkle proof

        Args:
            data: Original data
            proof: List of hashes forming the proof
            root_hash: Root hash of the Merkle tree
        """
        self.data = data
        self.proof = proof
        self.root_hash = root_hash

    def verify(self, tree: MerkleTree) -> bool:
        """
        Verify this proof against a Merkle tree

        Args:
            tree: Merkle tree to verify against

        Returns:
            bool: True if proof is valid
        """
        return tree.verify_proof(self.data, self.proof, self.root_hash)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation

        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            'data': self.data,
            'proof': self.proof,
            'root_hash': self.root_hash
        }

    @classmethod
    def from_dict(cls, proof_dict: Dict[str, Any]) -> 'MerkleProof':
        """
        Create from dictionary representation

        Args:
            proof_dict: Dictionary representation

        Returns:
            MerkleProof: A new MerkleProof instance
        """
        return cls(
            data=proof_dict['data'],
            proof=proof_dict['proof'],
            root_hash=proof_dict['root_hash']
        )
