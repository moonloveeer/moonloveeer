import pytest

from qrl.crypto.xmss import XMSS


def test_xmss_sign_and_verify_roundtrip():
    xmss = XMSS(height=4)
    message = b"hello-qrl"

    signature = xmss.sign(message)

    assert isinstance(signature, str)
    assert XMSS.verify(message, signature, xmss.get_public_key())
    assert not XMSS.verify(message + b"-tamper", signature, xmss.get_public_key())

    # Modify signature (flip last nibble) to ensure verification fails
    tampered_signature = signature[:-1] + ("0" if signature[-1] != "0" else "1")
    assert not XMSS.verify(message, tampered_signature, xmss.get_public_key())


def test_xmss_serialization_roundtrip():
    xmss = XMSS(height=6)
    original_address = xmss.get_address()
    original_pk = xmss.get_public_key()

    data = xmss.to_dict()
    restored = XMSS.from_dict(data)

    assert restored.get_address() == original_address
    assert restored.get_public_key() == original_pk
    assert restored.to_dict()["index"] == data["index"]


def test_xmss_index_exhaustion():
    with pytest.raises(ValueError):
        XMSS(height=2)

    xmss = XMSS(height=4)  # max_signatures = 16

    for _ in range(xmss.max_signatures):
        xmss.sign(b"payload")

    with pytest.raises(ValueError):
        xmss.sign(b"payload")
