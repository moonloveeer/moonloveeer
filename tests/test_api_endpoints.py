import importlib
import sys

import pytest

from qrl.core.transaction import Transaction


SAMPLE_SENDER = "0x" + "a" * 40
SAMPLE_RECIPIENT = "0x" + "b" * 40
PENDING_COUNTERPART = "0x" + "c" * 40


def _load_wallet_module(monkeypatch, tmp_path, auto_mine_value: str = "false"):
    data_dir = tmp_path / "wallet_data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("WEB_WALLET_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTO_MINE_ON_SEND", auto_mine_value)
    monkeypatch.setenv("SEED_BALANCE_QRL", "0")

    if "qrl.web_wallet" in sys.modules:
        del sys.modules["qrl.web_wallet"]

    wallet_module = importlib.import_module("qrl.web_wallet")
    wallet_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    wallet_module.node_service.blockchain.difficulty = 1
    wallet_module.node_service.mempool.clear()
    wallet_module.node_service.blockchain.pending_transactions = []

    return wallet_module


@pytest.fixture
def wallet_env(tmp_path, monkeypatch):
    module = _load_wallet_module(monkeypatch, tmp_path)
    client = module.app.test_client()
    return {
        "client": client,
        "module": module,
    }


def _add_pending_transaction(node_service, sender, recipient, amount, fee=1.0, signature_suffix=""):
    tx = Transaction(
        sender=sender,
        recipient=recipient,
        amount=amount,
        fee=fee,
        signature=f"sig{signature_suffix or amount}"
    )
    added = node_service.mempool.add_transaction(tx)
    assert added, "Failed to add pending transaction to mempool"
    return tx


def test_api_wallet_pending_totals(wallet_env):
    client = wallet_env["client"]
    module = wallet_env["module"]
    address = "0x" + "d" * 40

    module.node_service.mempool.clear()

    _add_pending_transaction(module.node_service, SAMPLE_SENDER, address, amount=25.0, signature_suffix="in")
    _add_pending_transaction(module.node_service, address, SAMPLE_RECIPIENT, amount=10.0, signature_suffix="out")

    response = client.get(f"/api/wallet/{address}")
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["address"].lower() == address.lower()
    assert payload["balance"] == pytest.approx(0.0, abs=1e-9)
    assert payload["pending_in"] == pytest.approx(25.0, rel=1e-6)
    assert payload["pending_out"] == pytest.approx(10.0, rel=1e-6)


def test_api_blocks_and_transactions(wallet_env):
    client = wallet_env["client"]
    module = wallet_env["module"]
    node_service = module.node_service

    miner = node_service.create_wallet()

    for index in range(3):
        _add_pending_transaction(
            node_service,
            SAMPLE_SENDER,
            SAMPLE_RECIPIENT,
            amount=50.0 + index,
            signature_suffix=f"confirmed-{index}"
        )
        node_service.mine_block()

    pending_tx = _add_pending_transaction(
        node_service,
        PENDING_COUNTERPART,
        SAMPLE_RECIPIENT,
        amount=12.5,
        signature_suffix="pending"
    )

    blocks_resp = client.get("/api/blocks?count=2")
    assert blocks_resp.status_code == 200
    blocks_payload = blocks_resp.get_json()
    assert "blocks" in blocks_payload
    assert len(blocks_payload["blocks"]) == 2
    assert blocks_payload["count"] == 2

    tx_resp = client.get("/api/transactions?limit=12&pending=true")
    assert tx_resp.status_code == 200
    tx_payload = tx_resp.get_json()
    assert "transactions" in tx_payload
    assert any(item.get("block_hash") is None for item in tx_payload["transactions"]), "Expected pending transaction in response"
    assert any(item.get("transaction_hash") == pending_tx.transaction_hash for item in tx_payload["transactions"])

    tx_resp_no_pending = client.get("/api/transactions?limit=12&pending=false")
    assert tx_resp_no_pending.status_code == 200
    tx_payload_no_pending = tx_resp_no_pending.get_json()
    assert all(item.get("block_hash") for item in tx_payload_no_pending["transactions"])


def test_api_block_detail_success_and_not_found(wallet_env):
    client = wallet_env["client"]
    module = wallet_env["module"]
    node_service = module.node_service

    node_service.create_wallet()
    _add_pending_transaction(node_service, SAMPLE_SENDER, SAMPLE_RECIPIENT, amount=75.0, signature_suffix="mine")
    node_service.mine_block()

    latest_block = node_service.blockchain.chain[-1]
    success_resp = client.get(f"/api/block/{latest_block.hash}")
    assert success_resp.status_code == 200
    success_payload = success_resp.get_json()
    assert success_payload["hash"] == latest_block.hash
    assert success_payload["index"] == latest_block.index

    missing_resp = client.get("/api/block/ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    assert missing_resp.status_code == 404
    missing_payload = missing_resp.get_json()
    assert missing_payload["error"] == "Block not found"
