"""Entry point: report (+ context, + optional human answer) -> decisions/<name>.json (Contract 2).

python -m agent.run --report reports/ev_market.pdf --context contexts/analyst_client_note.json [--offline] [--human "..."]
--report also accepts a parsed JSON (Contract 1). Offline = deterministic mock panel, no network, no cost.
"""
import argparse
import asyncio
import json
import hashlib
import re
from pathlib import Path

from agent import core, panel

ROOT = Path(__file__).resolve().parent.parent
import os
PARSED = ROOT / "parsed"
DECISIONS = Path(os.environ.get("CONDORCET_OUT", ROOT / "decisions"))


def load_parsed(report):
    p = Path(report)
    if p.suffix.lower() == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    raise ValueError("Supported inputs are transcribed parsed/*.json reports; PDF ingestion is unavailable.")


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
    a = (answer or "").lower().strip()
    # The UI records the reviewer's explicit choice; unresolved wording must never count as confirmation.
    if a.startswith("inconclusive:"):
        return {"confirmed": set(), "denied": set(), "reading": "is inconclusive about"}
    if a.startswith("denied:"):
        return {"denied": {flip_ref}, "confirmed": set(), "reading": "denies"}
    if a.startswith("confirmed:"):
        return {"confirmed": {flip_ref}, "denied": set(), "reading": "confirms"}
    if re.search(r"\b(not confirmed|unconfirmed|cannot confirm|can't confirm|could not confirm|not verified|unverified|uncertain)\b", a):
        return {"confirmed": set(), "denied": set(), "reading": "is inconclusive about"}
    if a.startswith("denied:") or re.search(r"\b(wrong|false|incorrect|not true|not correct|deny|denied)\b|^no[,.\s]", a):
        return {"denied": {flip_ref}, "confirmed": set(), "reading": "denies"}
    if re.search(r"\b(confirm|confirmed|verified|correct|true|yes|accurate|checked)\b", a):
        return {"confirmed": {flip_ref}, "denied": set(), "reading": "confirms"}
    return {"confirmed": set(), "denied": set(), "reading": "is inconclusive about"}


def run(report, context_path, offline, human_answer=None, dry_run=False, human_ref=None,
        full_evidence=False, replay_path=None, output_name=None):
    parsed = load_parsed(report)
    context = json.loads(Path(context_path).read_text(encoding="utf-8"))
    name = parsed["report"]
    artifact_name = output_name or (name + (".full" if full_evidence else ""))
    if not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*", artifact_name):
        raise ValueError("Invalid output artifact name")
    out_path = DECISIONS / f"{artifact_name}.json"
    prev = json.loads(out_path.read_text(encoding="utf-8")) if (human_answer and out_path.exists()) else None

    pieces = core.build_evidence(parsed)
    human = {"confirmed": set(), "denied": set()}
    always = []
    if human_answer:
        if not prev:
            raise ValueError("Run an initial decision before adding a human answer.")
        flip_ref = human_ref or (prev.get("human") or {}).get("ref") or (prev.get("flip_evidence") or {}).get("ref")
        if flip_ref not in {p["ref"] for p in pieces}:
            raise ValueError("Select a valid evidence reference for the human answer.")
        human = interpret_human(human_answer, flip_ref)
        pieces.append({"id": "H1", "kind": "human", "ref": flip_ref,
                       "summary": f'H1 {context["accountable"]} on {flip_ref}: "{human_answer}"'})
        always = ["H1"]
    by_id = {p["id"]: p for p in pieces}
    judges = list(panel.JUDGES)
    base = [p for p in pieces if p["kind"] != "human"]
    seen, r = core.subspaces(base, judges, always=always)
    if full_evidence:
        seen = {j: [p["id"] for p in pieces] for j in judges}
        r = len(judges)

    use_llm = bool(replay_path) or not offline
    if not offline and not replay_path and not panel.has_key() and not dry_run:
        raise ValueError("Live mode requires API configuration. Use --offline explicitly for simulated judges.")
    provenance = None
    votes, failed = [], []
    if dry_run:
        prompts = {j: panel.build_prompt(parsed, context, by_id, seen[j], core.evidence_text) for j in judges}
        chars = sum(len(p) for p in prompts.values())
        print(f"[dry-run] {len(prompts)} calls, ~{chars // 4:,} input tokens total (~4 chars/token); nothing sent.")
        print("[dry-run] first prompt:\n" + next(iter(prompts.values())))
        return None
    if replay_path:
        if human_answer:
            raise ValueError("Historical votes cannot be reused for a different human answer.")
        source_path = Path(replay_path)
        source_bytes = source_path.read_bytes()
        source = json.loads(source_bytes)
        source_panel = source.get("panel", {})
        if source.get("report") != name or source.get("context") != context or source_panel.get("mode") != "llm":
            raise ValueError("The historical votes do not match this report and context.")
        expected_condition = "full_evidence" if full_evidence else "subspace"
        if source_panel.get("condition") != expected_condition:
            raise ValueError("The historical evidence condition does not match this replay.")
        source_base = [p for p in source.get("evidence", []) if p.get("kind") != "human"]
        if source_base != base:
            raise ValueError("Historical evidence differs from the current parsed report.")
        seen_judges = set()
        for old in source_panel.get("votes", []):
            j = old.get("judge")
            try:
                if j not in seen or j in seen_judges or old.get("model") != panel.JUDGES[j]:
                    raise ValueError("Unexpected or repeated judge")
                seen_judges.add(j)
                if old.get("saw") != seen[j]:
                    raise ValueError("Historical evidence exposure does not match")
                if re.search(r"unparseable|not valid json|defaulted", old.get("why", ""), re.I):
                    raise ValueError("The original parser marked this reply malformed")
                action, cited, why = panel.parse_vote(json.dumps({k: old.get(k) for k in ("action", "cited", "why")}), seen[j])
                votes.append({"judge": j, "model": panel.JUDGES[j], "saw": seen[j], "action": action,
                              "cited": cited, "why": why, "cached": True, "historical": True})
            except (ValueError, TypeError):
                failed.append({"judge": j, "model": old.get("model"), "error": "Excluded during saved-vote validation"})
        failed.extend({"judge": f.get("judge"), "model": f.get("model"), "error": "Original run: provider failure"}
                      for f in source_panel.get("failed", []))
        if len(votes) < 5:
            raise ValueError("Fewer than five valid historical votes; refusing to decide.")
        provenance = {"kind": "revalidated_saved_votes", "source_file": source_path.name,
                      "sha256": hashlib.sha256(source_bytes).hexdigest(), "new_api_calls": 0,
                      "limitation": "Validation uses saved structured votes; original raw model replies and request cache were not supplied."}
    elif use_llm:
        prompts = {j: panel.build_prompt(parsed, context, by_id, seen[j], core.evidence_text) for j in judges}
        replies = asyncio.run(panel.run_llm_panel(prompts))
        for j, (text, cached, err) in zip(judges, replies):
            if err:
                failed.append({"judge": j, "model": panel.JUDGES[j], "error": err})
                continue
            try:
                action, cited, why = panel.parse_vote(text, seen[j])
            except ValueError:
                failed.append({"judge": j, "model": panel.JUDGES[j], "error": "Invalid or uncited judge reply"})
                continue
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
    if flip and d["status"] == "INFO_GAP":
        reasons.append({"text": f'Votes are associated with exposure to {flip["ref"]} (shown {flip["saw_it"]}, '
                                f'not shown {flip["didnt"]}). The exposure groups may differ on other evidence; this does not establish cause.',
                        "evidence": [flip["id"], flip["ref"]]})
    elif flip:
        reasons.append({"text": f'Votes differ across evidence slices (around {flip["ref"]}: saw it {flip["saw_it"]}, '
                                f'did not {flip["didnt"]}); the exposure test does not explain this split, so a human decides', "evidence": [flip["id"], flip["ref"]]})
    b = d["baseline"]
    reasons.append({"text": f'Simple-rule baseline ({b["rule"]}): {b["action"]}'
                            + (f' focusing on {b["focus"]}' if b["focus"] else "")
                            + f'. Panel adds beyond the rule: {"YES, " if d["panel_adds"]["value"] else "no; "}{d["panel_adds"]["detail"]}',
                    "evidence": [b["focus"]] if b["focus"] else []})
    if human_answer:
        reasons.append({"text": f'{context["accountable"]} {human.get("reading", "answered about")} '
                                f'{flip_ref}; a human statement does not remove the hard-rule floor',
                        "evidence": ["H1"]})

    question = None
    question_piece = None
    confirmed_refs = human.get("confirmed", set())
    rule_ids = {eid for rule in d["hard_rules"] if rule["triggered"] for eid in rule["evidence"]}
    rule_piece = next((p for p in base if p["id"] in rule_ids and p["kind"] == "claim" and p["ref"] not in confirmed_refs), None)
    if rule_piece and d["action"] in ("BLOCK", "ESCALATE"):
        question_piece = rule_piece
        question = (f'{rule_piece["ref"]} is flagged by the safety rule: "{rule_piece["text"][:160]}". '
                    f'Can you confirm or correct it from a source you trust?')
    elif d["status"] in ("FRAGILE", "INFO_GAP") and flip:
        fp = by_id[flip["id"]]
        question_piece = fp
        question = (f'The decision depends on {flip["ref"]}: "{fp["summary"][:160]}". '
                    f'Can you confirm or correct it from a source you trust?')
    elif d["action"] == "ESCALATE":
        from collections import Counter as _C
        top = _C(c for v in votes if v["action"] == "ESCALATE" for c in v["cited"]).most_common(1)
        if top:
            fp = by_id[top[0][0]]
            question_piece = fp
            question = (f'The most-cited escalation reason is {fp["ref"]}: "{fp["summary"][:160]}". '
                        f'Can you confirm it, or should we cut it?')
    headline = {
        "STABLE": f'Judges agree ({d["top_share"]:.0%}) with {"full evidence" if full_evidence else "sampled evidence slices"} → {d["action"]}.',
        "INFO_GAP": (f'Votes differ by exposure to {flip["ref"]} → {d["action"]}; check this association and the flagged evidence. '
                     f'Asking {context["accountable"]} to verify it.' if flip else d["action"]),
        "FRAGILE": (f'Judges differ across evidence slices (around {flip["ref"]}); asking {context["accountable"]}.' if flip
                    else f'Judges split; {d["action"]}.'),
    }[d["status"]]

    result = {
        "report": name, "question": parsed.get("question"), "context": context,
        "action": d["action"], "status": d["status"], "headline": headline,
        "evidence": [{k: v for k, v in p.items() if k != "sources"} | ({"sources": p["sources"]} if p["kind"] == "claim" else {})
                     for p in pieces],
        "panel": {"n_judges": len(votes), "n_failed": len(failed), "failed": failed, "r": r,
                  "mode": "llm" if use_llm else "offline-mock", "condition": "full_evidence" if full_evidence else "subspace",
                  "votes": votes, "tally": d["tally"], "top_action": d["top_action"], "top_share": d["top_share"]},
        "flip_evidence": flip, "hard_rules": d["hard_rules"], "load_bearing": sorted(lb),
        "baseline": d["baseline"], "panel_adds": d["panel_adds"],
        "reasons": reasons, "unchecked": unchecked(parsed),
        "human": {"to": context["accountable"], "ref": flip_ref if human_answer else (question_piece or {}).get("ref"), "question": question if not human_answer else
                  (prev or {}).get("human", {}).get("question"), "answer": human_answer},
        "before": ({"action": prev["action"], "status": prev["status"], "tally": prev["panel"]["tally"]} if prev else None),
        "trace": [f"parsed {len(parsed['claims'])} claims, {len(parsed.get('findings', []))} findings",
                  f"{len(base)} evidence pieces; each shown to {r} of {len(judges)} judges",
                  f"panel mode: {'LLM via TokenRouter' if use_llm else 'simulated judges (rule-based)'}",
                  f"tally {d['tally']} → {d['status']}",
                  f"hard floor: {[r_['rule'] for r_ in d['hard_rules'] if r_['triggered']] or 'none triggered'}",
                  f"final action: {d['action']}"], "provenance": provenance,
    }
    DECISIONS.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(result, indent=1, default=list), encoding="utf-8")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--context", required=True)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--human", default=None)
    ap.add_argument("--human-ref", default=None, help="explicit evidence reference for the human answer")
    ap.add_argument("--full-evidence", action="store_true", help="control: all judges see all evidence")
    ap.add_argument("--replay-votes", default=None, help="revalidate a saved real-model decision without API calls")
    ap.add_argument("--output-name", default=None)
    ap.add_argument("--dry-run", action="store_true", help="build the real prompts, print cost estimate, send nothing")
    a = ap.parse_args()
    r = run(a.report, a.context, a.offline, a.human, a.dry_run, a.human_ref, a.full_evidence, a.replay_votes, a.output_name)
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
