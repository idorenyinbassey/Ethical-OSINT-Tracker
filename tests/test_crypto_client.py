"""app.services.crypto_client — BTC/ETH address lookup. Both _btc() and
_eth() now extract "counterparties" (the other party's address on each
recent transaction) from the same response data already being fetched, so
crypto investigations can hub-link on the graph when two looked-up
addresses have actually transacted with each other."""
from unittest.mock import patch
from app.services import crypto_client


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json


class _FakeClient:
    def __init__(self, response):
        self._response = response

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, **kwargs):
        return self._response


def _client_factory(response):
    def factory(timeout=10):
        return _FakeClient(response)
    return factory


# lookup_address() is @cached(ttl=300), so each test below uses its own
# unique address to avoid reading back a previous test's mocked result.
OTHER_BTC_ADDR = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"


def test_btc_extracts_counterparty_on_send():
    addr = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfN1"
    tx = {
        "hash": "abc123",
        "time": 1000,
        "result": -50000000,
        "inputs": [{"prev_out": {"addr": addr}}],
        "out": [{"addr": OTHER_BTC_ADDR}, {"addr": addr}],  # + change back to self
    }
    data = {"total_received": 0, "total_sent": 50000000, "final_balance": 0, "n_tx": 1, "txs": [tx]}
    with patch.object(crypto_client, "get_http_client", _client_factory(_FakeResponse(data))):
        result = crypto_client.lookup_address(addr)

    assert result["counterparties"] == [OTHER_BTC_ADDR]


def test_btc_extracts_counterparty_on_receive():
    addr = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfN2"
    tx = {
        "hash": "def456",
        "time": 2000,
        "result": 50000000,
        "inputs": [{"prev_out": {"addr": OTHER_BTC_ADDR}}],
        "out": [{"addr": addr}],
    }
    data = {"total_received": 50000000, "total_sent": 0, "final_balance": 50000000, "n_tx": 1, "txs": [tx]}
    with patch.object(crypto_client, "get_http_client", _client_factory(_FakeResponse(data))):
        result = crypto_client.lookup_address(addr)

    assert result["counterparties"] == [OTHER_BTC_ADDR]


def test_btc_dedupes_counterparties_across_txs():
    addr = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfN3"
    tx1 = {"hash": "a", "time": 1, "result": -1, "inputs": [{"prev_out": {"addr": addr}}],
           "out": [{"addr": OTHER_BTC_ADDR}]}
    tx2 = {"hash": "b", "time": 2, "result": -1, "inputs": [{"prev_out": {"addr": addr}}],
           "out": [{"addr": OTHER_BTC_ADDR}]}
    data = {"total_received": 0, "total_sent": 2, "final_balance": 0, "n_tx": 2, "txs": [tx1, tx2]}
    with patch.object(crypto_client, "get_http_client", _client_factory(_FakeResponse(data))):
        result = crypto_client.lookup_address(addr)

    assert result["counterparties"] == [OTHER_BTC_ADDR]


def test_btc_handles_missing_addr_fields_gracefully():
    # Multisig / OP_RETURN outputs often have no "addr" key at all.
    addr = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfN4"
    tx = {"hash": "a", "time": 1, "result": -1, "inputs": [{"prev_out": {"addr": addr}}],
          "out": [{"value": 100}]}
    data = {"total_received": 0, "total_sent": 1, "final_balance": 0, "n_tx": 1, "txs": [tx]}
    with patch.object(crypto_client, "get_http_client", _client_factory(_FakeResponse(data))):
        result = crypto_client.lookup_address(addr)

    assert result["counterparties"] == []


OTHER_ETH_ADDR = "0x00000000000000000000000000000000000000be"  # 42 chars


def test_eth_extracts_counterparty_and_populates_recent_txs():
    addr = "0x000000000000000000000000000000000000dea1"  # 42 chars
    tx = {
        "hash": "0xabc",
        "confirmed": "2024-01-01T00:00:00Z",
        "inputs": [{"addresses": [addr]}],
        "outputs": [{"addresses": [OTHER_ETH_ADDR]}],
    }
    data = {"final_balance": 0, "total_received": 0, "total_sent": 0, "n_tx": 1, "txs": [tx]}
    with patch.object(crypto_client, "get_http_client", _client_factory(_FakeResponse(data))):
        result = crypto_client.lookup_address(addr)

    assert result["counterparties"] == [OTHER_ETH_ADDR]
    assert len(result["recent_txs"]) == 1


def test_eth_returns_empty_counterparties_when_no_txs():
    addr = "0x000000000000000000000000000000000000dea2"  # 42 chars
    data = {"final_balance": 0, "total_received": 0, "total_sent": 0, "n_tx": 0, "txs": []}
    with patch.object(crypto_client, "get_http_client", _client_factory(_FakeResponse(data))):
        result = crypto_client.lookup_address(addr)

    assert result["counterparties"] == []
    assert result["recent_txs"] == []


def test_unrecognised_address_format_returns_error():
    result = crypto_client.lookup_address("not-an-address")
    assert "error" in result
