import json
import pytest

from agent import core, run
from ui.data import ROOT


def test_flip_never_reuses_hard_rule_evidence():
    pieces = [
        {"id": "E1", "ref": "C1", "kind": "claim", "verdict": "Contradicted"},
        {"id": "E2", "ref": "C2", "kind": "claim", "verdict": "Supported"},
    ]
    votes = [{"action": "BLOCK", "saw": ["E1"], "cited": ["E1"]}] * 4
    votes += [{"action": "APPROVE", "saw": ["E2"], "cited": []}] * 5
    d = core.decide(votes, pieces, {"stakes": "high"}, {"C1"})
    assert d["flip_evidence"] is None
    assert d["action"] != "APPROVE"


def test_zero_association_is_not_a_flip():
    piece = {"id": "E1", "ref": "C1"}
    votes = [{"action": "REWRITE", "saw": ["E1"], "cited": ["E1"]},
             {"action": "REWRITE", "saw": [], "cited": []}]
    assert core.flip_evidence(votes, [piece]) is None


def test_calendar_adjacency_handles_month_boundary():
    assert core._days("2024-02-29", "2024-03-01") == 1
    assert core._days("2024-12-31", "2025-01-01") == 1


@pytest.mark.parametrize("full,stem,count,share", [(False, "ev_market.llm_subspace", 5, .8), (True, "ev_market.llm_full_evidence", 7, .857)])
def test_historical_replay_excludes_bad_votes(monkeypatch, full, stem, count, share):
    output = ROOT / "cache/test-replay"
    output.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(run, "DECISIONS", output)
    r = run.run(ROOT / "parsed/ev_market.json", ROOT / "contexts/analyst_client_note.json", False,
                full_evidence=full, replay_path=ROOT / "reports/experiments" / f"{stem}.original.json", output_name=stem)
    assert r["panel"]["n_judges"] == count
    assert r["panel"]["top_share"] == share
    assert r["action"] == "REWRITE" and r["status"] == "STABLE"
    assert r["provenance"]["new_api_calls"] == 0
    assert all(v["cited"] for v in r["panel"]["votes"])


def test_live_mode_does_not_silently_simulate(monkeypatch):
    monkeypatch.setattr(run.panel, "has_key", lambda: False)
    with pytest.raises(ValueError, match="API configuration"):
        run.run(ROOT / "parsed/ev_market.json", ROOT / "contexts/analyst_client_note.json", False)
