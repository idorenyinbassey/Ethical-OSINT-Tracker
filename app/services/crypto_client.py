"""Blockchain/cryptocurrency address lookup using free public APIs (no API key)."""
from app.services.cache import cached
from app.utils.proxy_config import get_http_client


def _detect_type(address: str) -> str:
    a = address.strip()
    if a.startswith(("1", "3", "bc1")):
        return "bitcoin"
    if a.startswith("0x") and len(a) == 42:
        return "ethereum"
    return "unknown"


@cached(ttl=300)
def lookup_address(address: str) -> dict:
    address = address.strip()
    coin_type = _detect_type(address)

    if coin_type == "bitcoin":
        return _btc(address)
    if coin_type == "ethereum":
        return _eth(address)
    return {"error": "Unrecognised address format. Supports Bitcoin (1/3/bc1) and Ethereum (0x).", "address": address}


def _btc(address: str) -> dict:
    try:
        with get_http_client(timeout=10) as client:
            r = client.get(f"https://blockchain.info/rawaddr/{address}", params={"limit": "5"})
        if r.status_code == 200:
            data = r.json()
            return {
                "address": address,
                "coin": "Bitcoin",
                "total_received_btc": round(data.get("total_received", 0) / 1e8, 8),
                "total_sent_btc": round(data.get("total_sent", 0) / 1e8, 8),
                "balance_btc": round(data.get("final_balance", 0) / 1e8, 8),
                "tx_count": data.get("n_tx", 0),
                "recent_txs": [
                    {
                        "hash": tx.get("hash", "")[:16] + "...",
                        "time": tx.get("time", 0),
                        "result_btc": round(tx.get("result", 0) / 1e8, 8),
                    }
                    for tx in data.get("txs", [])[:5]
                ],
            }
        return {"address": address, "coin": "Bitcoin", "error": f"HTTP {r.status_code}"}
    except Exception as exc:
        return {"address": address, "coin": "Bitcoin", "error": str(exc)}


def _eth(address: str) -> dict:
    try:
        with get_http_client(timeout=10) as client:
            r = client.get(
                "https://api.blockcypher.com/v1/eth/main/addrs/" + address + "/balance"
            )
        if r.status_code == 200:
            data = r.json()
            balance_wei = data.get("final_balance", 0)
            return {
                "address": address,
                "coin": "Ethereum",
                "balance_eth": round(balance_wei / 1e18, 8),
                "total_received_eth": round(data.get("total_received", 0) / 1e18, 8),
                "total_sent_eth": round(data.get("total_sent", 0) / 1e18, 8),
                "tx_count": data.get("n_tx", 0),
            }
        return {"address": address, "coin": "Ethereum", "error": f"HTTP {r.status_code}"}
    except Exception as exc:
        return {"address": address, "coin": "Ethereum", "error": str(exc)}
