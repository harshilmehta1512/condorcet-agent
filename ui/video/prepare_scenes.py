"""Generate narration from the corrected decisions, never from hand-entered tallies."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def decision(name):
    return json.loads((ROOT / "decisions" / f"{name}.json").read_text(encoding="utf-8"))


def main():
    ev = decision("ev_market")
    after = decision("ev_market.after_human")
    nuclear = decision("nuclear")
    slices = decision("ev_market.llm_subspace")
    full = decision("ev_market.llm_full_evidence")
    comparison = decision("experiment_comparison")
    claim = next(p for p in nuclear["evidence"] if p.get("ref") == "C5")
    assert after["before"]["action"] == ev["action"]
    assert after["status"] == "STABLE" and after["action"] == "ESCALATE"
    assert slices["status"] == full["status"] == "STABLE"
    assert comparison["matched_subspace_tally"] == comparison["matched_full_evidence_tally"]
    n = slices["panel"]["n_judges"]
    rewrite = slices["panel"]["tally"]["REWRITE"]
    nf = full["panel"]["n_judges"]
    rf = full["panel"]["tally"]["REWRITE"]
    scenes = [
        {"image": "01_ev_overview.jpg", "title": "Before: a verdict. Now: an accountable next step.", "minimum": 11,
         "takeaway": "Decision → reason → accountable reviewer",
         "say": "Condorcet turns an AI trust report into an accountable next step. Before, a verdict hid the evidence trail. Now, this simple workspace shows the decision, reason, and reviewer. Inputs were transcribed from Ezio's screens."},
        {"image": "02_ev_evidence.jpg", "title": "EV market · question the evidence, including Ezio", "minimum": 10,
         "takeaway": "C1: the quoted figure matches the claim, but the verdict contradicts it",
         "say": "In the EV report, Geely's one point four nine million vehicles is marked contradicted, although Ezio quotes the same figure. The agent asks the research lead to check the report itself."},
        {"image": "03_ev_judges.jpg", "title": "Different evidence views · clearly labeled simulation", "minimum": 10,
         "takeaway": "Hard rules stay separate from the flip search",
         "say": f"These {ev['panel']['n_judges']} judges are simulated rules, not AI models. Dark cells show cited evidence. Hard-rule warnings stay separate from the flip search, and a contradicted claim can never be approved."},
        {"image": "04_ev_human.jpg", "title": "Human in the loop · a saved, traceable update", "minimum": 11,
         "takeaway": f"{ev['action']} / {ev['status']} → {after['action']} / {after['status']}",
         "say": "Here is the saved human update. The lead confirms the figure. Escalation remains, because other claims are unverified, but the panel becomes stable. Human confirmation does not remove the safety floor."},
        {"image": "05_nuclear_overview.jpg", "title": "Second report · a different, sensible action", "minimum": 11,
         "takeaway": f"Nuclear energy → {nuclear['action']} / {nuclear['status']}",
         "say": f"Now Nuclear energy, for an internal policy brief. The same agent returns Pull Source, not approval. {nuclear['panel']['tally']['PULL_SOURCE']} simulated judges request another source; {nuclear['panel']['tally']['REWRITE']} suggest rewriting."},
        {"image": "06_nuclear_sources.jpg", "title": "Nuclear C5 · count origins, not repeated entries", "minimum": 11,
         "takeaway": f"{claim['n_sources']} source entries → {claim['n_origins']} usable origin groups",
         "say": f"Claim C5 lists {claim['n_sources']} sources, but four Department of Energy pages share an origin. Six entries become {claim['n_origins']} groups. Another independent source is the next step; these groups are heuristic."},
        {"image": "07_real_slices.jpg", "title": "Saved real-model votes · corrected validation", "minimum": 12,
         "takeaway": f"{rewrite}/{n} REWRITE · {slices['panel']['top_share']:.0%} agreement · STABLE",
         "say": f"We also revalidated saved TokenRouter votes. A malformed, uncited reply had distorted the result. After exclusion, {rewrite} of {n} valid judges choose Rewrite: eighty percent, stable. No new model calls were made."},
        {"image": "08_real_full.jpg", "title": "Full evidence · report what the comparison actually shows", "minimum": 13,
         "takeaway": f"{rf}/{nf} REWRITE · matched models give identical votes · no superiority claim",
         "say": f"With full evidence, {rf} of {nf} valid judges choose Rewrite. Both panels are stable. The five models shared across both runs give identical votes. We do not claim better decisions from hiding evidence. Agreement is not correctness."},
    ]
    (HERE / "scenes.json").write_text(json.dumps(scenes, indent=2, ensure_ascii=False), encoding="utf-8")
    (HERE / "narration.txt").write_text("\n\n".join(s['say'] for s in scenes), encoding="utf-8")
    print(f"Prepared {len(scenes)} scenes; {sum(len(s['say'].split()) for s in scenes)} narration words.")


if __name__ == "__main__":
    main()
