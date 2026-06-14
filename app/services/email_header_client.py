"""Email header analyser — parses raw headers to trace routing path and detect anomalies."""
import email as _email
import re
from email import policy


def analyse_headers(raw: str) -> dict:
    msg = _email.message_from_string(raw, policy=policy.default)

    def _h(key: str) -> str:
        return str(msg.get(key, "") or "")

    result = {
        "from": _h("From"),
        "to": _h("To"),
        "subject": _h("Subject"),
        "date": _h("Date"),
        "message_id": _h("Message-ID"),
        "reply_to": _h("Reply-To"),
        "x_mailer": _h("X-Mailer"),
        "x_originating_ip": _h("X-Originating-IP"),
        "spf": _h("Received-SPF"),
        "dkim_present": bool(msg.get("DKIM-Signature")),
        "dmarc": _h("Authentication-Results"),
        "received_chain": [],
        "flags": [],
    }

    for received in msg.get_all("Received") or []:
        raw_hop = str(received).strip()
        hop: dict = {"raw": raw_hop[:500]}
        ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", raw_hop)
        if ips:
            hop["ips"] = list(dict.fromkeys(ips))
        m = re.search(r"from\s+(\S+)", raw_hop, re.IGNORECASE)
        if m:
            hop["from_host"] = m.group(1)
        m = re.search(r"by\s+(\S+)", raw_hop, re.IGNORECASE)
        if m:
            hop["by_host"] = m.group(1)
        result["received_chain"].append(hop)

    flags = result["flags"]
    if result["x_originating_ip"]:
        flags.append(f"Originating IP detected: {result['x_originating_ip']}")
    if result["spf"] and "fail" in result["spf"].lower():
        flags.append("SPF FAILED — sender may be spoofed")
    elif not result["spf"]:
        flags.append("No SPF result found")
    if not result["dkim_present"]:
        flags.append("No DKIM signature — message authenticity unverified")
    if result["reply_to"] and result["reply_to"] != result["from"]:
        flags.append(f"Reply-To differs from From: {result['reply_to']}")

    return result
