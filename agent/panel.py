"""[5] Judge panel: real LLM judges via TokenRouter (cached) or a deterministic offline mock."""
import asyncio
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("CONDORCET_CACHE", ROOT / "cache"))

_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"'))

# short name -> TokenRouter model id. Fill/confirm at T2; keep >= 5 families.
JUDGES = {
    "gpt-nano": "gpt-5.4-nano", "gpt-mini": "gpt-5.4-mini",
    "haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5",
    "gemini": "gemini-flash-latest", "llama": "llama-latest", "qwen": "qwen-latest",
    "mistral": "mistral-small-latest", "deepseek": "deepseek-chat",
}

PROMPT = """You are one member of a review panel deciding what should happen next with an AI-generated answer.

WHO RELIES ON IT: {role}, who wants to use it for: {use}. Stakes: {stakes}. Accountable human: {accountable}.
ORIGINAL QUESTION: {question}
AI ANSWER (analyzed text, may be truncated):
{answer}

A verification tool (Ezio) produced a trust report. You are shown ONLY these pieces of its evidence:
{evidence}

Choose exactly one next action:
APPROVE (safe to use as is), REWRITE (fix or hedge specific sentences), PULL_SOURCE (get another independent source first),
ESCALATE (an accountable human must decide), BLOCK (must not be used).
Base your choice only on the evidence shown. Evidence marked [H1] is a statement from the accountable human; treat it as authoritative for the claim it names. Note how many INDEPENDENT origins back each claim, not how many sources are listed.
Reply with JSON only: {{"action": "...", "cited": ["E1", ...], "why": "one sentence"}}"""


def build_prompt(parsed, context, pieces_by_id, seen, evidence_text):
    ev = "\n".join(f"[{pid}] {evidence_text(pieces_by_id[pid])}" for pid in seen)
    return PROMPT.format(role=context["role"], use=context["use"], stakes=context["stakes"],
                         accountable=context["accountable"], question=parsed.get("question", "?"),
                         answer=parsed.get("analyzed_text", "")[:2500], evidence=ev)


def parse_vote(text, seen):
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        d = {}
    action = str(d.get("action", "")).upper().strip()
    if action not in ("APPROVE", "REWRITE", "PULL_SOURCE", "ESCALATE", "BLOCK"):
        hit = re.search(r"APPROVE|REWRITE|PULL_SOURCE|ESCALATE|BLOCK", (text or "").upper())
        action = hit.group(0) if hit else "ESCALATE"  # unparseable -> conservative, logged in `why`
        d.setdefault("why", "unparseable reply; defaulted to ESCALATE")
    cited = [c for c in d.get("cited", []) if c in seen]
    return action, cited, str(d.get("why", ""))[:300]


# ---------- offline mock (docs/03 §3 row 12) ----------
def mock_vote(seen, pieces_by_id, context, human):
    cited, action, why = [], "APPROVE", "all evidence shown looks supported by independent origins"
    rank = {"APPROVE": 0, "REWRITE": 1, "PULL_SOURCE": 2, "ESCALATE": 3, "BLOCK": 4}

    def bump(a, pid, w):
        nonlocal action, why
        cited.append(pid)
        if rank[a] > rank[action]:
            action, why = a, w

    for pid in seen:
        p = pieces_by_id[pid]
        if p["kind"] == "claim":
            if p["ref"] in human.get("confirmed", ()):
                continue
            v = p["verdict"].lower()
            if p["ref"] in human.get("denied", ()) or re.search(r"contradict|refut|false", v):
                bump("BLOCK" if context["stakes"] == "high" else "REWRITE", pid, f"{p['ref']} is contradicted")
            elif re.search(r"not enough|unverif|insufficient|unclear", v):
                bump("ESCALATE" if context["stakes"] == "high" else "PULL_SOURCE", pid, f"{p['ref']} is unverified")
            elif p["n_sources"] >= 2 and p["n_origins"] == 1:
                bump("PULL_SOURCE", pid, f"{p['ref']}: {p['n_sources']} sources but 1 independent origin")
        elif p["kind"] == "scores" and re.search(r"bias [12]\b", p["summary"]):
            bump("REWRITE", pid, "bias score shows one-sided framing")
        elif p["kind"] == "finding" and p.get("severity", "").upper() == "CRITICAL" and p["ref"] not in human.get("confirmed", ()):
            wording = re.search(r"agree|flatter|sycophan|tone|framing|bias", p["summary"], re.I)
            bump("REWRITE" if wording else "ESCALATE", pid,
                 f"critical finding {p['ref']}" + (" (wording: rewrite it)" if wording else ""))
    return action, cited, why


# ---------- real panel ----------
def _content(resp_json):
    """Chat-completions content as text; tolerate list-of-parts content."""
    c = resp_json["choices"][0]["message"].get("content")
    if isinstance(c, list):
        c = "".join(part.get("text", "") for part in c if isinstance(part, dict))
    return (c or "").strip()


async def _call(client, model, prompt):
    """Returns (text, cached, error). Errors are never turned into votes (bug B4)."""
    key = hashlib.sha256(f"{model}\n{prompt}".encode()).hexdigest()
    path = CACHE / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())["text"], True, None
    base = os.environ["TOKENROUTER_BASE_URL"].rstrip("/")
    headers = {"Authorization": f"Bearer {os.environ['TOKENROUTER_API_KEY']}"}
    # 1st try: classic params. 2nd try: reasoning-model params (no temperature, max_completion_tokens).
    bodies = [{"temperature": 0, "max_tokens": 400}, {"max_completion_tokens": 2000}]
    variant, err = 0, None
    for attempt in range(4):
        try:
            async with _SEM:
                r = await client.post(f"{base}/chat/completions", headers=headers,
                                      json={"model": model, "messages": [{"role": "user", "content": prompt}],
                                            **bodies[variant]})
            if r.status_code in (401, 402, 403, 404):  # auth / credit / unknown model: retrying won't help
                return None, False, f"HTTP {r.status_code}: {r.text[:200]}"
            if r.status_code == 400 and variant == 0:  # likely rejects temperature/max_tokens: use reasoning params
                variant, err = 1, f"HTTP 400: {r.text[:200]}"
                continue
            if r.status_code >= 400:  # 429 / 5xx: back off and retry
                err = f"HTTP {r.status_code}: {r.text[:200]}"
                await asyncio.sleep(2 * (attempt + 1))
                continue
            text = _content(r.json())
            if not text:  # reasoning model spent the budget thinking: retry with the bigger budget
                variant, err = 1, "empty reply"
                continue
            CACHE.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"model": model, "text": text}))
            return text, False, None
        except Exception as e:  # network error: back off and retry
            err = f"{type(e).__name__}: {e}"
            await asyncio.sleep(2 * (attempt + 1))
    return None, False, err


_SEM = None


async def run_llm_panel(prompts):
    global _SEM
    import httpx
    _SEM = asyncio.Semaphore(4)  # at most 4 calls in flight
    async with httpx.AsyncClient(timeout=90) as client:
        return await asyncio.gather(*(_call(client, JUDGES[j], p) for j, p in prompts.items()))


def has_key():
    return bool(os.environ.get("TOKENROUTER_BASE_URL") and os.environ.get("TOKENROUTER_API_KEY"))
