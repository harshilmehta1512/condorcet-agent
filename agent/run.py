"""Entry point: report (+ context, + optional human answer) -> decisions/<name>.json (Contract 2).

python -m agent.run --report reports/ev_market.pdf --context contexts/analyst_client_note.json [--offline] [--human "..."]
--report also accepts a parsed JSON (Contract 1). Offline = deterministic mock panel, no network, no cost.
"""
import argparse
import asyncio
import json
import re
from pathlib import Path

from agent import core, panel

ROOT = Path(__file__).resolve().parent.parent
import os
PARSED = ROOT / "parsed"
DECISIONS = Path(os.environ.get("CONDORCET_OUT", ROOT / "decisions"))


def load_parsed(report):
    p = Path(report)
    if p.suffix == ".json":
        return json.loads(p.read_text())
    from agent.parse_report import parse_pdf
    parsed = parse_pdf(p)
    PARSED.mkdir(exist_ok=True)
    (PARSED / f"{parsed['report']}.json").write_text(json.dumps(parsed, indent=1))
    return parsed


def load_bearing(parsed):
    """Offline rule (docs/03 §6 fallback): every claim is load-bearing unless it has no number, date or proper noun."""
    # Ezio extracts at most 5 "important" claims per report, so every extracted claim is treated as load-bearing.
    return {c["id"] for c in parsed["claims"]}


def unchecked(parsed):
    claims = [c["text"] for c in parsed["claims"]]
    out = []
    for s in re.split(r"(?<=[.!?])\s+", parsed.get("analyzed_text", "")):
        if re.search(r"\d", s) and len(s) > 30 and all(core._jaccard(s, c) < 0.3 for c in claims):
            out.append(s.strip())
    return out[:6]


def interpret_human(answer, flip_ref):
    """Offline keyword mapping (docs/03 §3 row 11) of the human's reply onto the flip claim/finding."""
    a = (answer or "").lower()
    if re.search(r"\b(wrong|false|incorrect|not true|deny|denied|no,)\b", a):
        return {"denied": {flip_ref}, "confirmed": set(), "reading": "denies"}
    if re.search(r"\b(confirm|confirmed|verified|correct|true|yes|accurate|checked)\b", a):
        return {"confirmed": {flip_ref}, "denied": set(), "reading": "confirms"}
    return {"confirmed": set(), "denied": set(), "reading": "is inconclusive about"}


def run(report, context_path, offline, human_answer=None, dry_run=False):
    parsed = load_parsed(report)
    context = json.loads(Path(context_path).read_text())
    name = parsed["report"]
    out_path = DECISIONS / f"{name}.json"
    prev = json.loads(out_path.read_text()) if (human_answer and out_path.exists()) else None

    pieces = core.build_evidence(parsed)
    human = {"confirmed": set(), "denied": set()}
    always = []
    if human_answer and prev and prev.get("flip_evidence"):
        flip_ref = prev["flip_evidence"]["ref"]
        human = interpret_human(human_answer, flip_ref)
        pieces.append({"id": "H1", "kind": "human", "ref": flip_ref,
                       "summary": f'H1 {context["accountable"]} on {flip_ref}: "{human_answer}"'})
        always = ["H1"]
    by_id = {p["id"]: p for p in pieces}
    judges = list(panel.JUDGES)
    base = [p for p in pieces if p["kind"] != "human"]
    seen, r = core.subspaces(base, judges, always=always)

    use_llm = not offline and panel.has_key()
    votes, failed = [], []
    if dry_run:
        prompts = {j: panel.build_prompt(parsed, context, by_id, seen[j], core.evidence_text) for j in judges}
        chars = sum(len(p) for p in prompts.values())
        print(f"[dry-run] {len(prompts)} calls, ~{chars // 4:,} input tokens total (~4 chars/token); nothing sent.")
        print("[dry-run] first prompt:\n" + next(iter(prompts.values())))
        return None
    if use_llm:
        prompts = {j: panel.build_prompt(parsed, context, by_id, seen[j], core.evidence_text) for j in judges}
        replies = asyncio.run(panel.run_llm_panel(prompts))
        for j, (text, cached, err) in zip(judges, replies):
            if err:
                failed.append({"judge": j, "model": panel.JUDGES[j], "error": err})
                continue
            action, cited, why = panel.parse_vote(text, seen[j])
            votes.append({"judge": j, "model": panel.JUDGES[j], "saw": seen[j], "action": action,
                          "cited": cited, "why": why, "cached": cached})
        if len(votes) < 5:
            raise SystemExit(f"Only {len(votes)} of {len(judges)} judges answered; refusing to decide on a panel this small. "
                             f"Failures: {failed}")
    else:
        for j in judges:
            action, cited, why = panel.mock_vote(seen[j], by_id, context, human)
            votes.append({"judge": j, "model": "offline-mock", "saw": seen[j], "action": action,
                          "cited": cited, "why": why, "cached": True})

    lb = load_bearing(parsed)
    overrides = human.get("confirmed", set())
    d = core.decide(votes, base, context, lb, overrides)
    flip = d["flip_evidence"]

    reasons = []
    for p in base:
        if p["kind"] == "claim" and p["n_sources"] >= 2 and p["n_origins"] < p["n_sources"]:
            pre = f' ({len(p["predating"])} published before the period it covers)' if p.get("predating") else ""
            reasons.append({"text": f'{p["ref"]} lists {p["n_sources"]} sources but only {p["n_origins"]} independent origin(s) could confirm it{pre}',
                            "evidence": [p["id"], p["ref"]] + [s["id"] for s in p["sources"]]})
    for p in base:  # Ezio verdict that contradicts its own quoted evidence
        if p["kind"] == "claim" and re.search(r"contradict", p["verdict"], re.I):
            nums = set(re.findall(r"\d+(?:\.\d+)?", p["verdict"].split("(", 1)[-1]))
            if nums & set(re.findall(r"\d+(?:\.\d+)?", p["text"])):  # claim text only (bug B3)
                reasons.append({"text": f'{p["ref"]}: Ezio marks it contradicted, but the figure it quotes from its sources '
                                        f'matches the claim; the verdict itself needs a human check', "evidence": [p["id"], p["ref"]]})
    m = parsed.get("modules", {})
    if isinstance(m.get("bias"), int) and m["bias"] <= 2:
        reasons.append({"text": f'Ezio bias score {m["bias"]}/5: the answer leans to one side; a balanced rewrite is needed before it is used',
                        "evidence": [p["id"] for p in base if p["kind"] == "scores"]})
    if not isinstance(m.get("accuracy"), int):
        reasons.append({"text": f'Ezio could not score accuracy ({m.get("accuracy")}): too few checkable claims, so silence is not support',
                        "evidence": [p["id"] for p in base if p["kind"] == "scores"]})
    for rule in d["hard_rules"]:
        if rule["triggered"]:
            reasons.append({"text": f'Hard rule: {rule["rule"]}', "evidence": rule["evidence"]})
    reasons.append({"text": f'Panel: {d["tally"]}; top action {d["top_action"]} at {d["top_share"]:.0%} '
                            f'({"≥" if d["status"] == "STABLE" else "<"} {core.STABLE_SHARE:.0%} needed) → {d["status"]}',
                    "evidence": sorted({c for v in votes for c in v["cited"]})})
    if flip:
        fp = by_id[flip["id"]]
        reasons.append({"text": f'Decision depends on {flip["id"]} ({flip["ref"]}): judges who saw it {flip["saw_it"]}, '
                                f'judges who did not {flip["didnt"]}', "evidence": [flip["id"], flip["ref"]]})
    if human_answer:
        reasons.append({"text": f'{context["accountable"]} {human.get("reading", "answered about")} '
                                f'{prev["flip_evidence"]["ref"] if prev and prev.get("flip_evidence") else "the flagged evidence"}',
                        "evidence": ["H1"]})

    question = None
    if d["status"] == "FRAGILE" and flip:
        fp = by_id[flip["id"]]
        question = (f'The decision depends on {flip["ref"]}: "{fp["summary"][:160]}". '
                    f'Can you confirm or correct it from a source you trust?')
    elif d["action"] == "ESCALATE":
        from collections import Counter as _C
        top = _C(c for v in votes if v["action"] == "ESCALATE" for c in v["cited"]).most_common(1)
        if top:
            fp = by_id[top[0][0]]
            flip = {"id": fp["id"], "ref": fp["ref"], "tv": None, "saw_it": {}, "didnt": {}, "note": "most-cited by escalating judges"}
            question = (f'All judges escalate; the most-cited reason is {fp["ref"]}: "{fp["summary"][:160]}". '
                        f'Can you confirm it, or should we cut it?')
    headline = {
        "STABLE": f'Judges agree across different evidence slices ({d["top_share"]:.0%}) → {d["action"]}.',
        "FRAGILE": (f'Decision splits depending on {flip["ref"]}; asking {context["accountable"]}.' if flip
                    else f'Judges split; {d["action"]}.'),
    }[d["status"]]

    result = {
        "report": name, "question": parsed.get("question"), "context": context,
        "action": d["action"], "status": d["status"], "headline": headline,
        "evidence": [{k: v for k, v in p.items() if k != "sources"} | ({"sources": p["sources"]} if p["kind"] == "claim" else {})
                     for p in pieces],
        "panel": {"n_judges": len(votes), "n_failed": len(failed), "failed": failed, "r": r,
                  "mode": "llm" if use_llm else "offline-mock",
                  "votes": votes, "tally": d["tally"], "top_action": d["top_action"], "top_share": d["top_share"]},
        "flip_evidence": flip, "hard_rules": d["hard_rules"], "load_bearing": sorted(lb),
        "reasons": reasons, "unchecked": unchecked(parsed),
        "human": {"to": context["accountable"], "question": question if not human_answer else
                  (prev or {}).get("human", {}).get("question"), "answer": human_answer},
        "before": ({"action": prev["action"], "status": prev["status"], "tally": prev["panel"]["tally"]} if prev else None),
        "trace": [f"parsed {len(parsed['claims'])} claims, {len(parsed.get('findings', []))} findings",
                  f"{len(base)} evidence pieces; each shown to {r} of {len(judges)} judges",
                  f"panel mode: {'LLM via TokenRouter' if use_llm else 'offline mock'}",
                  f"tally {d['tally']} → {d['status']}",
                  f"hard floor: {[r_['rule'] for r_ in d['hard_rules'] if r_['triggered']] or 'none triggered'}",
                  f"final action: {d['action']}"],
    }
    DECISIONS.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(result, indent=1, default=list))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--context", required=True)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--human", default=None)
    ap.add_argument("--dry-run", action="store_true", help="build the real prompts, print cost estimate, send nothing")
    a = ap.parse_args()
    r = run(a.report, a.context, a.offline, a.human, a.dry_run)
    if r is None:
        return
    print(f'{r["report"]}: {r["action"]} ({r["status"]}) | tally {r["panel"]["tally"]} | mode {r["panel"]["mode"]}')
    print("  " + r["headline"])
    for x in r["reasons"]:
        print("  -", x["text"])
    if r["human"]["question"] and not r["human"]["answer"]:
        print(f'  ? to {r["human"]["to"]}: {r["human"]["question"]}')
    if r["before"]:
        print(f'  before: {r["before"]["action"]} ({r["before"]["status"]}) → after: {r["action"]} ({r["status"]})')


if __name__ == "__main__":
    main()
