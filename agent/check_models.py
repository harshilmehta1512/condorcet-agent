"""Step 1 before spending credit.
  python -m agent.check_models --list   # GET /models (free): which model IDs TokenRouter offers
  python -m agent.check_models          # 1 tiny call per configured judge (~9 calls, fractions of a cent)
"""
import asyncio
import os
import sys

import httpx

from agent import panel  # loads .env


def list_models():
    base = os.environ["TOKENROUTER_BASE_URL"].rstrip("/")
    r = httpx.get(f"{base}/models", headers={"Authorization": f"Bearer {os.environ['TOKENROUTER_API_KEY']}"}, timeout=30)
    print(f"GET /models -> HTTP {r.status_code}")
    if r.status_code == 200:
        ids = sorted(m.get("id", "?") for m in r.json().get("data", []))
        print(f"{len(ids)} models")
        for i in ids:
            print("  ", i)
    else:
        print("Model listing failed; check authentication or provider availability.")


async def ping():
    prompts = {j: 'Reply with JSON only: {"action": "APPROVE", "cited": [], "why": "ping"}' for j in panel.JUDGES}
    replies = await panel.run_llm_panel(prompts)
    ok = 0
    for (j, model), (text, cached, err) in zip(panel.JUDGES.items(), replies):
        status = "OK  " if text else "FAIL"
        ok += bool(text)
        print(f"{status} {j:12s} {model:28s} {(text or err or '')[:70]!r}")
    print(f"\n{ok}/{len(panel.JUDGES)} judges answer. Need >= 5 (ideally 9, >= 5 families). Fix FAIL ids in agent/panel.py JUDGES.")


if __name__ == "__main__":
    if not panel.has_key():
        sys.exit("Put TOKENROUTER_BASE_URL and TOKENROUTER_API_KEY in .env first.")
    list_models() if "--list" in sys.argv else asyncio.run(ping())
