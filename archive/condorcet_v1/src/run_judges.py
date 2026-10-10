"""Run all judges on conditions A and B -> results/results.jsonl (Contract 2).

Usage:
  python -m src.run_judges --pilot          # first N_PILOT items
  python -m src.run_judges                  # all items in data/items.jsonl
  python -m src.run_judges --n 60           # cut-down run (rule D2)
Provider is chosen by CONDORCET_PROVIDER = mock | tokenrouter (default mock: no network, no cost).
"""
import argparse
import asyncio
import json
from collections import Counter

from src import config
from src.llm_client import JudgeClient, build_prompt
from src.partition import build_assignments


def load_items():
    with open(config.ITEMS_PATH) as f:
        return [json.loads(l) for l in f]


async def _run_rows(items, assignments, client):
    by_id = {it["item_id"]: it for it in items}

    async def one(a):
        it = by_id[a["item_id"]]
        model = config.JUDGES[a["judge"]]
        informed = bool(set(a["shown_idx"]) & set(it["gold_idx"]))
        if not a["shown_idx"]:  # nothing to read: abstain without a call
            verdict, latency, cached = "NOT_ENOUGH_INFO", 0, True
        else:
            prompt = build_prompt(it["claim"], it["sentences"], a["shown_idx"])
            verdict, latency, cached = await client.judge(model, prompt, mock_ctx={"item": it, "shown_idx": a["shown_idx"]})
        return {"item_id": it["item_id"], "condition": a["condition"], "judge": a["judge"], "model": model,
                "shown_idx": a["shown_idx"], "informed": informed, "verdict": verdict, "gold": it["gold"],
                "latency_ms": latency, "cached": cached}

    return await asyncio.gather(*(one(a) for a in assignments))


async def run(items, provider=config.PROVIDER):
    client = JudgeClient(provider)
    try:
        return await _run_rows(items, build_assignments(items), client)
    finally:
        await client.close()


def run_single(item_id, provider=config.PROVIDER):
    """For the UI's live button (decision D10): Contract 2 rows for one item, both conditions."""
    items = [it for it in load_items() if it["item_id"] == item_id]
    return asyncio.run(run(items, provider))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--n", type=int, default=None)
    args = ap.parse_args()
    items = load_items()
    n = config.N_PILOT if args.pilot else (args.n or len(items))
    items = items[:n]
    print(f"provider={config.PROVIDER} items={len(items)} judges={config.N_JUDGES} R={config.R} "
          f"calls<= {len(items) * config.N_JUDGES * 2}")
    rows = asyncio.run(run(items))
    config.RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(config.RESULTS_PATH, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    (config.RESULTS_PATH.parent / "run_meta.json").write_text(json.dumps({"provider": config.PROVIDER, "n_items": len(items)}))
    parse_fail = Counter(r["judge"] for r in rows if r["verdict"] == "PARSE_FAIL")
    ok = 1 - sum(parse_fail.values()) / len(rows)
    print(f"wrote {len(rows)} rows -> {config.RESULTS_PATH} | parse ok {ok:.1%} | cached {sum(r['cached'] for r in rows)}")
    if parse_fail:
        print("parse failures by judge:", dict(parse_fail))
    if ok < 0.95:
        print("WARNING: parse rate < 95% — do not do the full run (rule A3).")


if __name__ == "__main__":
    main()
