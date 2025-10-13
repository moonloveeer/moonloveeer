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


@pytest.fixture(scope="module")
def wallet_client(tmp_path_factory, monkeypatch):
    tmp_path = tmp_path_factory.mktemp("api_fuzz")
    module = _load_wallet_module(monkeypatch, tmp_path)
    client = module.app.test_client()
    return client


@given(
    limit=st.integers(min_value=0, max_value=50),
    pending=st.booleans(),
)
def test_fuzz_transactions_endpoint(wallet_client, limit, pending):
    resp = wallet_client.get(f"/api/transactions?limit={limit}&pending={'true' if pending else 'false'}")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert isinstance(payload, dict)
    assert "transactions" in payload


@given(count=st.integers(min_value=0, max_value=10))
def test_fuzz_blocks_endpoint(wallet_client, count):
    resp = wallet_client.get(f"/api/blocks?count={count}")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert isinstance(payload, dict)
    assert "blocks" in payload


@given(addr=st.text(alphabet="0123456789abcdef", min_size=40, max_size=60))
def test_fuzz_wallet_endpoint(wallet_client, addr):
    address = "0x" + addr
    resp = wallet_client.get(f"/api/wallet/{address}")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert isinstance(payload, dict)
    assert payload.get("address").lower() == address.lower()
