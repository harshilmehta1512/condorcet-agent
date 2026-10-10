"""Regenerate every decision from inputs and saved historical votes. No inference calls."""
import json
from pathlib import Path
import shutil
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent import run

CASES = [("ev_market", "analyst_client_note"), ("nuclear", "policy_brief"),
         ("work_from_home", "comms_publish"), ("agi_timelines", "strategy_memo")]


def main():
    archive = ROOT / "reports/experiments/offline_before_fix"
    archive.mkdir(parents=True, exist_ok=True)
    for path in (ROOT / "decisions").glob("*.json"):
        if not (archive / path.name).exists():
            shutil.copyfile(path, archive / path.name)
    for name, context in CASES:
        result = run.run(ROOT / "parsed" / f"{name}.json", ROOT / "contexts" / f"{context}.json", True)
        print(name, result["action"], result["status"], result["panel"]["tally"], "flip", (result["flip_evidence"] or {}).get("ref"))
    for name, context, answer in [
        ("ev_market", "analyst_client_note", "Confirmed: Geely's 2024 annual report says 1.49 million new-energy vehicles."),
        ("agi_timelines", "strategy_memo", "Denied: the claimed 100% resolution and complete elimination of human bottlenecks is false."),
    ]:
        output_name = name + ".after_human"
        shutil.copyfile(ROOT / "decisions" / f"{name}.json", ROOT / "decisions" / f"{output_name}.json")
        result = run.run(ROOT / "parsed" / f"{name}.json", ROOT / "contexts" / f"{context}.json", True,
                         answer, human_ref="C1", output_name=output_name)
        print("Human", name, result["before"], "->", result["action"], result["status"])
    results = {}
    for full, name in [(False, "ev_market.llm_subspace"), (True, "ev_market.llm_full_evidence")]:
        result = run.run(ROOT / "parsed/ev_market.json", ROOT / "contexts/analyst_client_note.json", False,
                         full_evidence=full, replay_path=ROOT / "reports/experiments" / f"{name}.original.json", output_name=name)
        results["full" if full else "subspace"] = result
        print("Revalidated", name, result["action"], result["status"], result["panel"]["tally"], result["panel"]["top_share"])
    a = {v["model"]: v["action"] for v in results["subspace"]["panel"]["votes"]}
    b = {v["model"]: v["action"] for v in results["full"]["panel"]["votes"]}
    common = sorted(a.keys() & b.keys())
    summary = {
        "subspace": {k: results["subspace"]["panel"][k] for k in ("n_judges", "tally", "top_share", "n_failed")},
        "full_evidence": {k: results["full"]["panel"][k] for k in ("n_judges", "tally", "top_share", "n_failed")},
        "matched_models": common,
        "matched_subspace_tally": dict(Counter(a[m] for m in common)),
        "matched_full_evidence_tally": dict(Counter(b[m] for m in common)),
        "conclusion": "Both validated panels recommend REWRITE and are STABLE. Valid-answer model rosters differ; this does not establish that hiding evidence caused a change or improved decision quality.",
        "new_api_calls": 0,
    }
    (ROOT / "decisions/experiment_comparison.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
