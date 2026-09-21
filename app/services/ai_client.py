"""AI-assisted case analysis, strategy suggestions, and report summaries.

Two backends, never chained automatically into each other — which one runs
is always an explicit choice made by the caller/UI, not a silent fallback,
because they have very different privacy implications for a tool whose
whole premise is handling real investigation subjects' data responsibly:

- **Local (Ollama)**: the default. Runs entirely on the machine hosting
  this app — no API key, no network call leaves the box, no Settings
  configuration required at all (same "free by default" pattern as
  hibp_client's XposedOrNot fallback and paste_client's Cavalier lookup).
  Requires the admin to have Ollama installed and running
  (https://ollama.com) with a model pulled — this app never installs or
  manages Ollama itself.
- **Cloud (Google Gemini, free tier)**: strictly opt-in. Requires an admin
  to configure a `GeminiAI` API key in Settings. Using it sends the case
  digest (investigation summaries, team notes, journal entries — i.e.
  everything the app knows about a real investigation subject) to
  Google's servers. Every call site in this app that offers this must
  disclose that plainly before use, not bury it in a settings page.

LocalAI's own Settings row (if an admin creates one) is used only for
`is_enabled` (to fully disable local AI attempts) and `notes` (an optional
model-name override, e.g. "mistral" instead of the default "llama3.2") —
never for `base_url`. The endpoint is hardcoded to Ollama's own default
loopback address (127.0.0.1:11434) because `app.utils.validators.
validate_base_url()`'s SSRF protection deliberately rejects loopback/
private-IP base URLs, which is correct for every other service in this
app (an admin-facing config field should never be usable to probe internal
network services on an attacker's behalf) but would incorrectly block the
one service in this app that's *supposed* to be local by design. Routing
around the validator here — rather than weakening it — keeps that
protection intact for every real external service.

Neither backend's exact request/response contract has been independently
verified against live traffic at implementation time: this sandbox has no
Ollama installation to test against (a multi-GB model pull is impractical
here) and blocks generativelanguage.googleapis.com outright. Ollama's
`/api/generate` shape has been stable for a long time and is used here
with high confidence; Gemini's REST shape is also stable, but its
*model name* changes over time as Google ships new versions — the default
below should be verified/updated after deploying, and can be overridden
per-install via the GeminiAI config's `notes` field without a code change.
"""
import logging
from typing import Optional

from app.repositories.api_config_repository import get_by_service
from app.utils.proxy_config import get_http_client

logger = logging.getLogger(__name__)

_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
_OLLAMA_DEFAULT_MODEL = "llama3.2"

_GEMINI_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com"
# Verify/update after deploying — Google's free-tier model catalogue and
# naming changes over time; override without a code change via the
# GeminiAI config's `notes` field.
_GEMINI_DEFAULT_MODEL = "gemini-2.0-flash"


def _result(ok: bool, text: Optional[str] = None, source: str = "", error: Optional[str] = None) -> dict:
    return {"ok": ok, "text": text, "source": source, "error": error}


def is_local_available_by_config() -> bool:
    """Whether local AI is administratively enabled — does not check
    whether Ollama is actually installed/running (that's only knowable by
    trying the request), just whether an admin hasn't explicitly disabled
    it."""
    cfg = get_by_service("LocalAI")
    return not (cfg and not cfg.is_enabled)


def is_cloud_configured() -> bool:
    """Whether a GeminiAI key has been configured — the template uses this
    to decide whether to show the cloud option at all, so a case's
    analysis page never even offers to send data anywhere unless an admin
    has explicitly opted in by configuring a key."""
    cfg = get_by_service("GeminiAI")
    return bool(cfg and cfg.is_enabled and cfg.api_key)


def run_local(prompt: str, timeout: float = 60.0) -> dict:
    """Generate text via a local Ollama instance. Never raises — a missing/
    unreachable Ollama install degrades to a clear, actionable error
    rather than a stack trace, since this is expected to be common (most
    installs won't have Ollama running).
    """
    if not is_local_available_by_config():
        return _result(False, error="Local AI is disabled in Settings.")

    cfg = get_by_service("LocalAI")
    model = (cfg.notes.strip() if cfg and cfg.notes else "") or _OLLAMA_DEFAULT_MODEL

    try:
        with get_http_client(timeout=timeout) as client:
            r = client.post(_OLLAMA_URL, json={"model": model, "prompt": prompt, "stream": False})
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        logger.warning("Local AI (Ollama) request failed: %s", exc)
        return _result(False, error=(
            "Could not reach a local Ollama instance at 127.0.0.1:11434. "
            "Install Ollama (https://ollama.com), pull a model "
            f"(e.g. `ollama pull {model}`), and make sure it's running."
        ))

    text = data.get("response") if isinstance(data, dict) else None
    if not text:
        return _result(False, error=f"Ollama returned no text (model '{model}' may not be pulled).")
    return _result(True, text=text.strip(), source=f"Local AI (Ollama, {model})")


def run_cloud(prompt: str, timeout: float = 60.0) -> dict:
    """Generate text via Google Gemini's free-tier API. Only attempts the
    call when a GeminiAI key is actually configured — callers should also
    check is_cloud_configured() before ever presenting this as an option,
    since choosing to use it means the prompt (case data) is sent to
    Google.
    """
    cfg = get_by_service("GeminiAI")
    if not cfg or not cfg.is_enabled or not cfg.api_key:
        return _result(False, error="Cloud AI (Gemini) is not configured. Add a GeminiAI API key in Settings.")

    base = (cfg.base_url or _GEMINI_DEFAULT_BASE_URL).rstrip("/")
    model = (cfg.notes.strip() if cfg.notes else "") or _GEMINI_DEFAULT_MODEL
    url = f"{base}/v1beta/models/{model}:generateContent"

    try:
        with get_http_client(timeout=timeout) as client:
            r = client.post(url, params={"key": cfg.api_key},
                             json={"contents": [{"parts": [{"text": prompt}]}]})
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        logger.warning("Cloud AI (Gemini) request failed: %s", exc)
        return _result(False, error=f"Gemini request failed: {exc}")

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return _result(False, error=(
            f"Gemini returned an unexpected response shape (model '{model}' may be "
            "wrong or retired — check Settings → GeminiAI notes)."
        ))
    if not text:
        return _result(False, error="Gemini returned an empty response.")
    return _result(True, text=text.strip(), source=f"Cloud AI (Gemini, {model})")


def build_case_digest(case, investigations, comments, notes) -> str:
    """Condense a case's data into a compact text digest suitable for an
    LLM prompt — per-investigation key findings (not raw result_json,
    which is often large and mostly irrelevant noise for this purpose),
    plus team notes and journal entries. Reuses report_exporter's own
    per-kind field extraction so the digest highlights the same key facts
    a human-generated report would.
    """
    from app.services.report_exporter import _extract_findings

    lines = [f"Case: {case.title}", f"Status: {case.status} | Priority: {case.priority}"]
    if case.description:
        lines.append(f"Description: {case.description}")

    lines.append(f"\nInvestigations ({len(investigations)}):")
    for inv in investigations:
        findings = _extract_findings(inv.kind, inv.result_json)
        summary = "; ".join(f"{label}: {value}" for label, value in findings[:5])
        date = inv.created_at.strftime("%Y-%m-%d") if inv.created_at else "unknown date"
        lines.append(f"- [{date}] {inv.kind}: \"{inv.query}\" ({inv.confidence or 'UNVERIFIED'}) — {summary}")

    if notes:
        lines.append(f"\nInvestigator Journal ({len(notes)} entries):")
        for n in notes:
            lines.append(f"- ({n.kind}) {n.body}")

    if comments:
        lines.append(f"\nTeam Notes ({len(comments)} entries):")
        for c in comments:
            lines.append(f"- {c.username}: {c.body}")

    return "\n".join(lines)


_STRATEGY_PROMPT = """You are assisting an authorized OSINT investigator working a legitimate, authorized case. \
You are given a digest of everything investigated so far in this case. Based only on the information \
provided (do not invent facts, names, or data not present below):

1. Summarize the key findings and how they connect to each other.
2. Suggest concrete next investigative steps — be specific about what to look into and why, but only \
suggest actions consistent with lawful, ethical, authorized OSINT research (never suggest impersonation, \
account takeover, social engineering, or targeting anyone not already implicated in the case data below).
3. Flag anything that looks like a gap (an entity mentioned but never actually investigated) or a risk \
worth the investigator's attention.

Be concise and factual. This is advisory only — a human investigator will review and decide on any action.

Case digest:
{digest}
"""

_SUMMARY_PROMPT = """You are drafting the executive summary section of a formal OSINT investigation report, \
for an authorized case. Based only on the information provided below (do not invent facts), write a short, \
professional, neutral narrative paragraph or two summarizing what was investigated and what was found. \
This will be inserted into the case's Investigator Journal and may appear in exported reports, so write it \
as a factual record, not a recommendation.

Case digest:
{digest}
"""


def analyze_case(case, investigations, comments, notes, backend: str, analysis_type: str) -> dict:
    """Run either the local or cloud backend against a case's digest, with
    a prompt shaped for either investigative strategy suggestions or a
    report-style narrative summary. `backend` is "local" or "cloud" —
    always an explicit choice from the caller, never inferred or chained.
    """
    digest = build_case_digest(case, investigations, comments, notes)
    template = _STRATEGY_PROMPT if analysis_type == "strategy" else _SUMMARY_PROMPT
    prompt = template.format(digest=digest)

    runner = run_local if backend == "local" else run_cloud
    return runner(prompt)
