import importlib
import sys

import pytest
from hypothesis import given, strategies as st


def _load_wallet_module(monkeypatch, tmp_path, auto_mine_value: str = "false"):
    data_dir = tmp_path / "wallet_data_fuzz"
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


@pytest.fixture(scope="function")
def wallet_client(tmp_path_factory, monkeypatch):
    tmp_path = tmp_path_factory.mktemp("api_fuzz")
    module = _load_wallet_module(monkeypatch, tmp_path)
    client = module.app.test_client()
    return client


@pytest.mark.parametrize("limit,pending", [
    (0, True),
    (25, False),
    (50, True),
])
def test_transactions_endpoint(wallet_client, limit, pending):
    resp = wallet_client.get(f"/api/transactions?limit={limit}&pending={'true' if pending else 'false'}")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert isinstance(payload, dict)
    assert "transactions" in payload


@pytest.mark.parametrize("count", [0, 5, 10])
def test_blocks_endpoint(wallet_client, count):
    resp = wallet_client.get(f"/api/blocks?count={count}")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert isinstance(payload, dict)
    assert "blocks" in payload


def test_wallet_endpoint_not_found(wallet_client):
    # Test with a non-existent wallet address
    # Should return 200 with zero balance for non-existent addresses
    resp = wallet_client.get("/api/wallet/nonexistent123")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert isinstance(payload, dict)
    assert "balance" in payload
    assert payload["balance"] == 0.0


def test_wallet_endpoint_valid(wallet_client):
    # Test with a valid wallet address format (actual existence not required for this test)
    resp = wallet_client.get("/api/wallet/Q010400b1db5c2dffd89b84f83b52b1caa1d9bff3b4b1a57690e3c193f8dbf0e8b4a0f8e")
    # Should return 200 even if wallet doesn't exist (empty balance)
    assert resp.status_code == 200
    payload = resp.get_json()
    assert isinstance(payload, dict)
    assert "balance" in payload
    assert payload.get("address").lower() == "q010400b1db5c2dffd89b84f83b52b1caa1d9bff3b4b1a57690e3c193f8dbf0e8b4a0f8e"
