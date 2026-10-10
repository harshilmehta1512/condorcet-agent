"""Judge calls: prompt, parsing, disk cache, async OpenAI-compatible client, offline mock."""
import asyncio
import hashlib
import json
import random
import re
import time

import httpx

from src import config

PROMPT = """You are verifying a scientific claim using ONLY the evidence sentences below.
Claim: {claim}
Evidence:
{evidence}
If the evidence supports the claim, answer SUPPORT. If it contradicts the claim, answer CONTRADICT.
If this evidence is not enough to decide, answer NOT_ENOUGH_INFO. Do not use outside knowledge.
Reply with JSON only: {{"verdict": "SUPPORT" | "CONTRADICT" | "NOT_ENOUGH_INFO"}}"""

_VERDICT_RE = re.compile(r"NOT[_ ]ENOUGH[_ ]INFO|SUPPORT|CONTRADICT", re.IGNORECASE)


def build_prompt(claim, sentences, shown_idx):
    evidence = "\n".join(f"[{i}] {sentences[i]}" for i in shown_idx)
    return PROMPT.format(claim=claim, evidence=evidence)


def parse_verdict(text):
    """First verdict token in the reply; prefers the value of a "verdict" key if present."""
    if not text:
        return "PARSE_FAIL"
    m = re.search(r'"verdict"\s*:\s*"([^"]+)"', text)
    m = _VERDICT_RE.search(m.group(1) if m else text)
    if not m:
        return "PARSE_FAIL"
    return re.sub(r"[ ]", "_", m.group(0).upper())


def _cache_path(model, prompt):
    key = hashlib.sha256(f"{model}\n{prompt}".encode()).hexdigest()
    return config.CACHE_DIR / f"{key}.json"


class JudgeClient:
    def __init__(self, provider=config.PROVIDER):
        self.provider = provider
        if provider == "tokenrouter" and not (config.API_BASE_URL and config.API_KEY):
            raise RuntimeError("Set TOKENROUTER_BASE_URL and TOKENROUTER_API_KEY (event credits only, rule A1).")
        self.sem = asyncio.Semaphore(config.CONCURRENCY)
        self.http = httpx.AsyncClient(timeout=config.TIMEOUT_S) if provider == "tokenrouter" else None
        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    async def close(self):
        if self.http:
            await self.http.aclose()

    async def judge(self, model, prompt, mock_ctx=None):
        """Returns (verdict, latency_ms, cached). One retry on failure/parse fail."""
        path = _cache_path(f"{self.provider}:{model}", prompt)
        if path.exists():
            return parse_verdict(json.loads(path.read_text())["text"]), 0, True
        text, t0 = None, time.perf_counter()
        for _ in range(2):
            try:
                async with self.sem:
                    text = await (self._mock(model, mock_ctx) if self.provider == "mock" else self._call(model, prompt))
                if parse_verdict(text) != "PARSE_FAIL":
                    break
            except Exception as e:  # network / API error -> retry once
                text = f"ERROR: {e}"
        latency = int((time.perf_counter() - t0) * 1000)
        if text and not text.startswith("ERROR"):
            path.write_text(json.dumps({"model": model, "text": text}))
        return parse_verdict(text), latency, False

    async def _call(self, model, prompt):
        r = await self.http.post(
            f"{config.API_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {config.API_KEY}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0, "max_tokens": config.MAX_TOKENS},
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    async def _mock(self, model, ctx):
        """Offline stand-in with correlated errors: a shared per-item 'trap' fools most judges together."""
        it, shown_idx = ctx["item"], ctx["shown_idx"]
        rng = random.Random(f"{model}|{it['item_id']}|{shown_idx}")
        shared = random.Random(it["item_id"]).random() < 0.2  # item is a shared trap
        informed = bool(set(shown_idx) & set(it["gold_idx"]))
        wrong = "CONTRADICT" if it["gold"] == "SUPPORT" else "SUPPORT"
        if not informed:
            v = "NOT_ENOUGH_INFO" if rng.random() < 0.75 else rng.choice([it["gold"], wrong])
        elif shared and len(shown_idx) == len(it["sentences"]):
            v = wrong if rng.random() < 0.8 else it["gold"]
        else:
            v = it["gold"] if rng.random() < 0.85 else wrong
        await asyncio.sleep(0)
        return json.dumps({"verdict": v})
