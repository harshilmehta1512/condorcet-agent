import json
from pathlib import Path

import pytest

from agent import core, panel, run
from ui.data import ROOT, guide_message, read_json
from ui.review import submit_review

CASES = [("ev_market", "analyst_client_note"), ("nuclear", "policy_brief"),
         ("work_from_home", "comms_publish"), ("agi_timelines", "strategy_memo")]


@pytest.fixture
def output_dir(monkeypatch):
    path = ROOT / "cache" / "test-review"
    path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(run, "DECISIONS", path)
    return path


@pytest.mark.parametrize("name,context", CASES)
def test_repeatability_and_referenced_reasons(name, context, output_dir):
    a = run.run(ROOT / "parsed" / f"{name}.json", ROOT / "contexts" / f"{context}.json", True)
    b = run.run(ROOT / "parsed" / f"{name}.json", ROOT / "contexts" / f"{context}.json", True)
    assert a == b
    known = {p["id"] for p in a["evidence"]} | {p["ref"] for p in a["evidence"]}
    known |= {s["id"] for p in a["evidence"] for s in p.get("sources", [])}
    assert all(set(r["evidence"]) <= known for r in a["reasons"])


def test_human_confirmation_cannot_remove_contradiction_floor():
    piece = {"id": "E1", "ref": "C1", "kind": "claim", "verdict": "Contradicted"}
    votes = [{"action": "APPROVE", "saw": ["E1"], "cited": ["E1"]} for _ in range(9)]
    decision = core.decide(votes, [piece], {"stakes": "high"}, {"C1"}, {"C1"})
    assert decision["action"] != "APPROVE"
    assert decision["hard_rules"][0]["triggered"]


@pytest.mark.parametrize("answer", ["not confirmed", "cannot confirm this", "not verified", "Inconclusive: confirmed in one account only"])
def test_unresolved_answer_never_confirms(answer):
    assert not run.interpret_human(answer, "C1")["confirmed"]


@pytest.mark.parametrize("reply", ["bad JSON", '{"action":"BLOCK","cited":[],"why":"No evidence"}',
                                   '{"action":"APPROVE","cited":["E99"],"why":"Invented"}',
                                   '{"action":"APPROVE","cited":["E1"],"why":null}'])
def test_invalid_votes_are_rejected(reply):
    with pytest.raises(ValueError):
        panel.parse_vote(reply, ["E1"])


def test_valid_vote_retains_seen_citations():
    assert panel.parse_vote('{"action":"REWRITE","cited":["E1"],"why":"Wording issue"}', ["E1"]) == ("REWRITE", ["E1"], "Wording issue")


def test_explicit_human_target_survives_absent_flip(output_dir):
    before = run.run(ROOT / "parsed/nuclear.json", ROOT / "contexts/policy_brief.json", True)
    assert before["flip_evidence"] is None
    after = run.run(ROOT / "parsed/nuclear.json", ROOT / "contexts/policy_brief.json", True,
                    "Inconclusive: need another source", human_ref="C5")
    assert after["human"]["ref"] == "C5"
    assert any(p["id"] == "H1" for p in after["evidence"])
    assert all("H1" in v["saw"] for v in after["panel"]["votes"])
    assert after["before"]["action"] == before["action"]


def test_ui_review_preserves_demo_artifacts():
    import uuid
    name = "ev_market"
    snapshot = ROOT / "decisions" / f"{name}.json"
    original = snapshot.read_bytes()
    decision = json.loads(original)
    updated = submit_review(name, decision, "Confirmed: annual report says 1.49 million.", str(uuid.uuid4()))
    assert snapshot.read_bytes() == original
    assert updated["before"]["action"] == decision["action"]
    assert any(p["id"] == "H1" for p in updated["evidence"])
    assert updated["action"] != "APPROVE"


def test_safe_missing_and_invalid_artifacts(output_dir):
    assert read_json(output_dir / "missing.json")[0] is None
    invalid = output_dir / "invalid.json"
    invalid.write_text("not json", encoding="utf-8")
    assert read_json(invalid)[0] is None


def test_guide_never_claims_source_counts_are_globally_independent():
    d, _ = read_json(ROOT / "decisions/nuclear.json")
    message = guide_message(d, "Source independence")
    assert "heuristic groups" in message
