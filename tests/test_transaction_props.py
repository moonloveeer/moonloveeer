import pytest
from hypothesis import given, strategies as st

from qrl.core.transaction import Transaction
from qrl.crypto.xmss import XMSS


def qrl_address_strategy():
    hex_chars = st.text(alphabet="0123456789abcdef", min_size=40, max_size=70)
    return st.builds(lambda h: "Q" + h, hex_chars)


@given(amount=st.floats(min_value=1e-9, allow_nan=False, allow_infinity=False),
       fee=st.floats(min_value=0.0, allow_nan=False, allow_infinity=False),
       recipient=qrl_address_strategy())
def test_signed_transaction_valid(amount, fee, recipient):
    xmss = XMSS(height=10)
    sender = xmss.get_address()
    # ensure recipient differs from sender; if equal, tweak recipient
    if recipient == sender:
        recipient = recipient + "1"

    tx = Transaction(sender=sender, recipient=recipient, amount=amount, fee=fee)
    tx.sign_transaction(xmss)
    assert tx.is_valid() is True
    assert tx.get_total_amount() >= amount
    if amount > 0:
        assert tx.get_fee_percentage() >= 0.0


def test_coinbase_rules():
    # Coinbase tx: sender "0", positive amount, zero fee, no signature
    tx = Transaction(sender="0", recipient="Q" + "0" * 40, amount=1.0, fee=0.0)
    assert tx.signature is None
    assert tx.is_coinbase() is True
    assert tx.is_valid() is True


def test_invalid_same_sender_recipient():
    xmss = XMSS(height=10)
    addr = xmss.get_address()
    tx = Transaction(sender=addr, recipient=addr, amount=1.0, fee=0.0)
    tx.sign_transaction(xmss)
    assert tx.is_valid() is False
