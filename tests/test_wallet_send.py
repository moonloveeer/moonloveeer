import importlib
import sys

import pytest

from qrl.core.transaction import Transaction
from qrl.services.node_service import NodeService


SENDER_ADDRESS = "0x" + "a" * 40
RECIPIENT_ADDRESS = "0x" + "b" * 40


def _load_wallet_module(monkeypatch, tmp_path, auto_mine_value: str):
    data_dir = tmp_path / "wallet_data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("WEB_WALLET_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTO_MINE_ON_SEND", auto_mine_value)
    monkeypatch.setenv("SEED_BALANCE_QRL", "0")

    if "qrl.web_wallet" in sys.modules:
        del sys.modules["qrl.web_wallet"]

    wallet_module = importlib.import_module("qrl.web_wallet")
    wallet_module.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )

    # Keep tests fast/deterministic
    wallet_module.node_service.blockchain.difficulty = 1
    wallet_module.node_service.mempool.clear()
    wallet_module.node_service.blockchain.pending_transactions = []

    return wallet_module


def _prepare_user(wallet_module, address=SENDER_ADDRESS, balance=1_000.0):
    user = wallet_module.User(username="web3_test", wallet_address=address, is_web3=True)
    wallet_module.users_db[user.username] = user
    wallet_module.demo_balances[address] = balance
    return user


def test_send_auto_mine_enabled(tmp_path, monkeypatch):
    wallet_module = _load_wallet_module(monkeypatch, tmp_path, "true")
    client = wallet_module.app.test_client()

    user = _prepare_user(wallet_module)
    token = wallet_module.create_jwt_token(user)
    client.set_cookie("auth_token", token, domain="localhost")

    response = client.post(
        "/send",
        data={"recipient": RECIPIENT_ADDRESS, "amount": 50},
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)
    assert len(wallet_module.node_service.blockchain.chain) == 2
    assert wallet_module.node_service.mempool.get_pending_transactions() == []
    assert wallet_module.node_service.get_balance(RECIPIENT_ADDRESS) == pytest.approx(50.0, rel=1e-6)


def test_send_auto_mine_disabled(tmp_path, monkeypatch):
    wallet_module = _load_wallet_module(monkeypatch, tmp_path, "false")
    client = wallet_module.app.test_client()

    user = _prepare_user(wallet_module)
    token = wallet_module.create_jwt_token(user)
    client.set_cookie("auth_token", token, domain="localhost")

    response = client.post(
        "/send",
        data={"recipient": RECIPIENT_ADDRESS, "amount": 25},
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)
    assert len(wallet_module.node_service.blockchain.chain) == 1
    pending = wallet_module.node_service.mempool.get_pending_transactions()
    assert len(pending) == 1
    assert pending[0].recipient == RECIPIENT_ADDRESS
    assert wallet_module.node_service.get_balance(RECIPIENT_ADDRESS) == pytest.approx(0.0, abs=1e-9)


def test_node_service_mine_block_processes_pending(tmp_path):
    data_dir = tmp_path / "node"
    node_service = NodeService(data_dir=str(data_dir))
    node_service.blockchain.difficulty = 1

    miner_address = node_service.create_wallet()

    tx = Transaction(
        sender="0x" + "1" * 40,
        recipient="0x" + "2" * 40,
        amount=75.0,
        fee=1.0,
        signature="sig",
    )

    assert node_service.mempool.add_transaction(tx)

    mined = node_service.mine_block()

    assert mined is True
    assert len(node_service.blockchain.chain) == 2
    assert node_service.mempool.get_pending_transactions() == []
    assert node_service.get_balance(tx.recipient) == pytest.approx(75.0, rel=1e-6)
    assert node_service.get_balance(miner_address) > 0
