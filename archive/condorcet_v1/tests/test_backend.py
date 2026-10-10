import json

import numpy as np
import pytest

from src import analysis, config
from src.llm_client import build_prompt, parse_verdict
from src.partition import assign


def test_neff():
    assert analysis.n_eff(9, 0) == 9
    assert analysis.n_eff(9, 1) == 1
    assert analysis.n_eff(9, 0.4375) == pytest.approx(2.0)


def test_wilson():
    lo, hi = analysis.wilson(16, 20)
    assert lo == pytest.approx(0.584, abs=0.002)
    assert hi == pytest.approx(0.919, abs=0.002)
    assert analysis.wilson(0, 0) == [None, None]


@pytest.mark.parametrize("n_sent", [3, 8, 12, 20])
def test_partition(n_sent):
    shown = assign(n_sent, item_id=7, n_judges=9, r=4)
    counts = np.zeros(n_sent, int)
    for s in shown:
        assert s == sorted(s)
        counts[s] += 1
    assert (counts == 4).all()  # every sentence seen by exactly r judges
    assert shown == assign(n_sent, item_id=7, n_judges=9, r=4)  # deterministic
    if n_sent * 4 >= 9:
        assert all(shown)  # nobody empty when there are enough slots
    loads = [len(s) for s in shown]
    assert max(loads) - min(loads) <= 1  # balanced


@pytest.mark.parametrize("text,expected", [
    ('{"verdict": "SUPPORT"}', "SUPPORT"),
    ('```json\n{"verdict": "CONTRADICT"}\n```', "CONTRADICT"),
    ('{"verdict": "not_enough_info"}', "NOT_ENOUGH_INFO"),
    ("I think the answer is NOT ENOUGH INFO here.", "NOT_ENOUGH_INFO"),
    ('{"verdict": "SUPPORT"} — it does not CONTRADICT', "SUPPORT"),
    ("no idea", "PARSE_FAIL"),
    ("", "PARSE_FAIL"),
    (None, "PARSE_FAIL"),
])
def test_parse(text, expected):
    assert parse_verdict(text) == expected


def test_prompt_keeps_original_indices():
    p = build_prompt("c", ["s0", "s1", "s2"], [0, 2])
    assert "[0] s0" in p and "[2] s2" in p and "s1" not in p


def test_panel():
    assert analysis.panel_verdict(["SUPPORT", "SUPPORT", "CONTRADICT"]) == "SUPPORT"
    assert analysis.panel_verdict(["SUPPORT", "CONTRADICT", "NOT_ENOUGH_INFO"]) == "ESCALATE"  # tie
    assert analysis.panel_verdict(["NOT_ENOUGH_INFO", "PARSE_FAIL"]) == "ESCALATE"  # nobody committed
    assert analysis.panel_verdict(["NOT_ENOUGH_INFO", "CONTRADICT"]) == "CONTRADICT"  # abstain doesn't vote


def test_rho_identical_and_independent():
    rng = np.random.default_rng(0)
    e = rng.random(200) < 0.3
    C = np.ones((200, 3), bool)
    E = np.stack([e, e, rng.random(200) < 0.3], axis=1)
    M = analysis.rho_matrix(C, E)
    assert M[0, 1] == pytest.approx(1.0)
    assert abs(M[0, 2]) < 0.2


def _fake_rows(items, judges):
    rng = np.random.default_rng(1)
    rows = []
    for it in items:
        for cond in "AB":
            for j in judges:
                v = rng.choice(["SUPPORT", "CONTRADICT", "NOT_ENOUGH_INFO"], p=[0.6, 0.3, 0.1])
                rows.append({"item_id": it["item_id"], "condition": cond, "judge": j, "model": j,
                             "shown_idx": [0], "informed": bool(rng.random() < 0.6), "verdict": str(v),
                             "gold": it["gold"], "latency_ms": 0, "cached": False})
    return rows


def test_metrics_contract_keys():
    items = [{"item_id": i, "gold": "SUPPORT" if i % 3 else "CONTRADICT"} for i in range(40)]
    judges = ["a", "b", "c", "d", "e"]
    m = analysis.compute(_fake_rows(items, judges), items, judges, provider="mock")
    json.dumps(m)  # serialisable
    assert m["meta"]["FAKE"] is True
    for c in "AB":
        x = m["conditions"][c]
        for k in ("n_eff", "n_eff_ci", "rho_bar", "rho_matrix", "panel_acc", "panel_acc_ci", "coverage",
                  "condorcet_pred", "condorcet_gap", "best_single", "per_judge", "agreement_table", "false_consensus"):
            assert k in x, k
        assert len(x["rho_matrix"]) == 5
        assert x["n_eff"] <= 5
    for h in ("H1", "H2", "H3", "H4"):
        assert m["hypotheses"][h]["status"] in ("pass", "fail", "inconclusive")
