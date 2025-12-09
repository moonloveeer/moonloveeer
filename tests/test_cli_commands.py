import pytest
from click.testing import CliRunner

import qrl.cli.commands as cli


@pytest.fixture
def runner():
    return CliRunner()


def test_wallet_gen_creates_wallet(monkeypatch, runner):
    created = {}

    class DummyNode:
        def __init__(self):
            created["init"] = True

        def create_wallet(self, height):
            created["height"] = height
            return "Q12345"

    monkeypatch.setattr(cli, "NodeService", DummyNode)
    result = runner.invoke(cli.cli, ["wallet_gen", "--height", "12"])

    assert result.exit_code == 0
    assert "Wallet created with address: Q12345" in result.output
    assert created["height"] == 12


def test_wallet_info_without_wallet(monkeypatch, runner):
    class DummyNode:
        def __init__(self):
            pass

        def get_wallet_address(self):
            return None

        def get_balance(self, address):
            raise AssertionError("Balance should not be requested when wallet missing")

    monkeypatch.setattr(cli, "NodeService", DummyNode)
    result = runner.invoke(cli.cli, ["wallet_info"])

    assert result.exit_code == 0
    assert "No wallet found" in result.output


def test_wallet_info_with_wallet(monkeypatch, runner):
    class DummyNode:
        def __init__(self):
            self.address = "Q98765"

        def get_wallet_address(self):
            return self.address

        def get_balance(self, address):
            assert address == self.address
            return 42.5

    monkeypatch.setattr(cli, "NodeService", DummyNode)
    result = runner.invoke(cli.cli, ["wallet_info"])

    assert result.exit_code == 0
    assert "Wallet address: Q98765" in result.output
    assert "Balance: 42.5" in result.output


def test_tx_transfer_success(monkeypatch, runner):
    calls = {}

    class DummyNode:
        def __init__(self):
            calls["init"] = True

        def create_transaction(self, dst, amount):
            calls["dst"] = dst
            calls["amount"] = amount
            return True

    monkeypatch.setattr(cli, "NodeService", DummyNode)
    result = runner.invoke(cli.cli, ["tx_transfer", "--dst", "Q1", "--amount", "3.5"])

    assert result.exit_code == 0
    assert "Transaction created" in result.output
    assert calls["dst"] == "Q1"
    assert calls["amount"] == 3.5


def test_tx_transfer_failure(monkeypatch, runner):
    class DummyNode:
        def __init__(self):
            pass

        def create_transaction(self, dst, amount):
            return False

    monkeypatch.setattr(cli, "NodeService", DummyNode)
    result = runner.invoke(cli.cli, ["tx_transfer", "--dst", "Q1", "--amount", "1.0"])

    assert result.exit_code == 0
    assert "Failed to create transaction" in result.output


def test_mining_start(monkeypatch, runner):
    class DummyNode:
        def __init__(self):
            pass

        def mine_block(self):
            return True

    monkeypatch.setattr(cli, "NodeService", DummyNode)
    result = runner.invoke(cli.cli, ["mining_start"])

    assert result.exit_code == 0
    assert "Block mined successfully" in result.output
