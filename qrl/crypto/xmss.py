import os
from typing import Dict, Any, Optional

from pyqrllib import pyqrllib


XMSS_DEFAULT_SEED_BYTES = 48
XMSS_DEFAULT_HASH_FUNCTION = pyqrllib.SHAKE_128
XMSS_DEFAULT_ADDRESS_FORMAT = pyqrllib.SHA256_2X


def _bytes_to_uchar_vector(data: bytes) -> 'pyqrllib.ucharVector':
    """Convert bytes to pyqrllib's ucharVector."""
    return pyqrllib.ucharVector(list(data))


def _hex_to_uchar_vector(hex_string: str) -> 'pyqrllib.ucharVector':
    return pyqrllib.hstr2bin(hex_string)


class XMSS:
    """eXtended Merkle Signature Scheme (XMSS) wrapper backed by pyqrllib."""

    def __init__(self, height: int = 10, seed: Optional[bytes] = None):
        if height <= 0:
            raise ValueError("XMSS height must be positive")

        # XmssBasic defaults to BDS traversal with k=2. Enforce heights that satisfy
        # the library constraint: H - K must be even with H > K >= 2.
        if height < 4 or height % 2 != 0:
            raise ValueError("XMSS height must be an even integer >= 4")

        if seed is None:
            seed = os.urandom(XMSS_DEFAULT_SEED_BYTES)

        if not isinstance(seed, (bytes, bytearray)):
            raise TypeError("XMSS seed must be bytes or bytearray")

        if len(seed) != XMSS_DEFAULT_SEED_BYTES:
            raise ValueError(f"XMSS seed must be {XMSS_DEFAULT_SEED_BYTES} bytes")

        self.height = height
        self.seed = bytes(seed)
        self._xmss = pyqrllib.XmssBasic(
            _bytes_to_uchar_vector(self.seed),
            height,
            XMSS_DEFAULT_HASH_FUNCTION,
            XMSS_DEFAULT_ADDRESS_FORMAT,
        )

        self.max_signatures = 2 ** self.height
        self.index = self._xmss.getIndex()

    def _update_index(self) -> None:
        self.index = self._xmss.getIndex()

    def get_address(self) -> str:
        address_hex = pyqrllib.bin2hstr(self._xmss.getAddress())
        return f"Q{address_hex}"

    def get_public_key(self) -> str:
        return pyqrllib.bin2hstr(self._xmss.getPK())

    def get_private_key(self) -> str:
        return pyqrllib.bin2hstr(self._xmss.getSK())

    def sign(self, message: bytes) -> str:
        if not isinstance(message, (bytes, bytearray)):
            raise TypeError("Message must be bytes or bytearray")

        if self.index >= self.max_signatures:
            raise ValueError("All signatures have been used. Generate a new XMSS tree.")

        message_vec = _bytes_to_uchar_vector(bytes(message))
        signature_vec = self._xmss.sign(message_vec)
        self._update_index()
        return pyqrllib.bin2hstr(signature_vec)

    @staticmethod
    def verify(message: bytes, signature_hex: str, public_key_hex: str) -> bool:
        try:
            message_vec = _bytes_to_uchar_vector(bytes(message))
            signature_vec = _hex_to_uchar_vector(signature_hex)
            public_key_vec = _hex_to_uchar_vector(public_key_hex)
            return pyqrllib.XmssBasic.verify(message_vec, signature_vec, public_key_vec)
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'height': self.height,
            'seed': self.seed.hex(),
            'index': self._xmss.getIndex(),
            'max_signatures': self.max_signatures,
            'private_key': self.get_private_key(),
            'public_key': self.get_public_key(),
            'address': self.get_address(),
        }

    @classmethod
    def from_dict(cls, xmss_dict: Dict[str, Any]) -> 'XMSS':
        seed_hex = xmss_dict.get('seed')
        if not seed_hex:
            raise ValueError("XMSS dictionary is missing 'seed'")

        height = xmss_dict.get('height', 10)
        seed_bytes = bytes.fromhex(seed_hex)
        xmss = cls(height=height, seed=seed_bytes)

        index = xmss_dict.get('index', 0)
        xmss._xmss.setIndex(index)
        xmss._update_index()

        return xmss