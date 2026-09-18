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


def _btc_counterparties(tx: dict, address: str) -> list:
    """The other-party address(es) for a single blockchain.info tx, relative
    to `address` — the payees if this address paid out, the payers if it
    received. Best-effort: some inputs/outputs (multisig, OP_RETURN) have no
    `addr` field at all, and are simply skipped."""
    addr_lower = address.lower()
    input_addrs = [i.get("prev_out", {}).get("addr") for i in tx.get("inputs", [])]
    input_addrs = [a for a in input_addrs if a]
    output_addrs = [o.get("addr") for o in tx.get("out", [])]
    output_addrs = [a for a in output_addrs if a]

    if addr_lower in (a.lower() for a in input_addrs):
        # This address paid out — counterparties are the recipients,
        # excluding any change output back to itself.
        return [a for a in output_addrs if a.lower() != addr_lower]
    if addr_lower in (a.lower() for a in output_addrs):
        # This address received — counterparties are the senders.
        return [a for a in input_addrs if a.lower() != addr_lower]
    return []


def _btc(address: str) -> dict:
    try:
        with get_http_client(timeout=10) as client:
            r = client.get(f"https://blockchain.info/rawaddr/{address}", params={"limit": "5"})
        if r.status_code == 200:
            data = r.json()
            recent_txs = []
            counterparties: list = []
            for tx in data.get("txs", [])[:5]:
                for cp in _btc_counterparties(tx, address):
                    if cp not in counterparties:
                        counterparties.append(cp)
                recent_txs.append({
                    "hash": tx.get("hash", "")[:16] + "...",
                    "time": tx.get("time", 0),
                    "result_btc": round(tx.get("result", 0) / 1e8, 8),
                })
            return {
                "address": address,
                "coin": "Bitcoin",
                "total_received_btc": round(data.get("total_received", 0) / 1e8, 8),
                "total_sent_btc": round(data.get("total_sent", 0) / 1e8, 8),
                "balance_btc": round(data.get("final_balance", 0) / 1e8, 8),
                "tx_count": data.get("n_tx", 0),
                "recent_txs": recent_txs,
                "counterparties": counterparties[:10],
            }
        return {"address": address, "coin": "Bitcoin", "error": f"HTTP {r.status_code}"}
    except Exception as exc:
        return {"address": address, "coin": "Bitcoin", "error": str(exc)}


def _flatten_eth_addresses(items: list) -> list:
    addrs: list = []
    for item in items or []:
        addrs.extend(item.get("addresses") or [])
    return addrs


def _eth_counterparties(tx: dict, address: str) -> list:
    """Same other-party logic as _btc_counterparties(), for blockcypher's
    unified tx shape (its inputs/outputs each carry an "addresses" list —
    the same representation blockcypher uses across every chain it
    supports, including account-based ETH)."""
    addr_lower = address.lower()
    input_addrs = [a.lower() for a in _flatten_eth_addresses(tx.get("inputs", []))]
    output_addrs = [a.lower() for a in _flatten_eth_addresses(tx.get("outputs", []))]

    if addr_lower in input_addrs:
        return [a for a in output_addrs if a != addr_lower]
    if addr_lower in output_addrs:
        return [a for a in input_addrs if a != addr_lower]
    return []


def _eth(address: str) -> dict:
    try:
        with get_http_client(timeout=10) as client:
            # The plain /balance endpoint (used previously) never returns
            # transaction data at all. /full includes the same balance
            # fields plus full tx objects, so recent_txs/counterparties can
            # actually be populated instead of being permanently empty.
            r = client.get(
                f"https://api.blockcypher.com/v1/eth/main/addrs/{address}/full",
                params={"limit": "5"},
            )
        if r.status_code == 200:
            data = r.json()
            balance_wei = data.get("final_balance", data.get("balance", 0))
            recent_txs = []
            counterparties: list = []
            for tx in data.get("txs", [])[:5]:
                for cp in _eth_counterparties(tx, address):
                    if cp not in counterparties:
                        counterparties.append(cp)
                recent_txs.append({
                    "hash": (tx.get("hash") or "")[:16] + "...",
                    "time": tx.get("confirmed") or tx.get("received") or "",
                })
            return {
                "address": address,
                "coin": "Ethereum",
                "balance_eth": round(balance_wei / 1e18, 8),
                "total_received_eth": round(data.get("total_received", 0) / 1e18, 8),
                "total_sent_eth": round(data.get("total_sent", 0) / 1e18, 8),
                "tx_count": data.get("n_tx", 0),
                "recent_txs": recent_txs,
                "counterparties": counterparties[:10],
            }
        return {"address": address, "coin": "Ethereum", "error": f"HTTP {r.status_code}"}
    except Exception as exc:
        return {"address": address, "coin": "Ethereum", "error": str(exc)}
