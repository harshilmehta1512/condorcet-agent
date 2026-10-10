"""results.jsonl -> metrics.json (Contract 3). Pure computation: never calls a model (rule A2)."""
import datetime as dt
import json
import math
from collections import Counter

import numpy as np

from src import config

COMMITTED = ("SUPPORT", "CONTRADICT")
N_BOOT = 1000
N_SIM = 10_000
MIN_PAIR_ITEMS = 10


# ---------- formulas ----------
def n_eff(n, rho_bar):
    return n / (1 + (n - 1) * rho_bar)


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [round(centre - half, 4), round(centre + half, 4)]


def panel_verdict(verdicts):
    votes = Counter(v for v in verdicts if v in COMMITTED)
    if not votes:
        return "ESCALATE"
    (top, k), *rest = votes.most_common()
    if rest and rest[0][1] == k:
        return "ESCALATE"
    return top


# ---------- matrices ----------
def _matrices(rows, items, judges, cond):
    """V: verdict strings [items x judges]; C committed mask; E error mask; G gold."""
    idx = {it["item_id"]: i for i, it in enumerate(items)}
    V = np.full((len(items), len(judges)), "MISSING", dtype=object)
    for r in rows:
        if r["condition"] == cond and r["item_id"] in idx and r["judge"] in judges:
            V[idx[r["item_id"]], judges.index(r["judge"])] = r["verdict"]
    G = np.array([it["gold"] for it in items], dtype=object)
    C = np.isin(V, COMMITTED)
    E = C & (V != G[:, None])
    return V, C, E, G


def rho_matrix(C, E):
    """Phi correlation of error indicators over items where both judges committed."""
    n = C.shape[1]
    M = np.full((n, n), np.nan)
    for a in range(n):
        M[a, a] = 1.0
        for b in range(a + 1, n):
            both = C[:, a] & C[:, b]
            if both.sum() < MIN_PAIR_ITEMS:
                continue
            x, y = E[both, a].astype(float), E[both, b].astype(float)
            if x.std() == 0 or y.std() == 0:
                continue
            M[a, b] = M[b, a] = float(np.corrcoef(x, y)[0, 1])
    return M


def rho_bar(M):
    iu = np.triu_indices_from(M, k=1)
    vals = M[iu]
    vals = vals[~np.isnan(vals)]
    return float(vals.mean()) if len(vals) else float("nan")


def _panel(V, G):
    pv = np.array([panel_verdict(row) for row in V], dtype=object)
    decided = pv != "ESCALATE"
    correct = decided & (pv == G)
    return pv, decided, correct


def condorcet_prediction(V, G, rng):
    """Panel accuracy if judges were independent, each with its own observed correct/wrong/abstain rates."""
    valid = V != "PARSE_FAIL"
    probs = []
    for j in range(V.shape[1]):
        v, g = V[valid[:, j], j], G[valid[:, j]]
        n = max(len(v), 1)
        pc = np.sum((v == g) & np.isin(v, COMMITTED)) / n
        pw = np.sum((v != g) & np.isin(v, COMMITTED)) / n
        p = np.clip([pc, pw, 1 - pc - pw], 0, None)  # float error can make the remainder slightly negative
        probs.append(p / p.sum())
    draws = np.stack([rng.choice(3, size=N_SIM, p=p) for p in probs], axis=1)  # 0 correct 1 wrong 2 abstain
    nc, nw = (draws == 0).sum(1), (draws == 1).sum(1)
    decided = nc != nw
    return float((nc[decided] > nw[decided]).mean()) if decided.any() else float("nan")


def agreement_table(V, G, decided):
    groups = {}
    for row, g, d in zip(V, G, decided):
        if not d:
            continue
        votes = Counter(v for v in row if v in COMMITTED)
        (top, k), m = votes.most_common(1)[0], sum(votes.values())
        groups.setdefault(f"{k}/{m}", []).append(top == g)
    out = []
    for key, ok in groups.items():
        out.append({"k_of_committed": key, "count": len(ok), "acc": round(float(np.mean(ok)), 4),
                    "ci": wilson(int(np.sum(ok)), len(ok))})
    return sorted(out, key=lambda r: (-int(r["k_of_committed"].split("/")[1]), -int(r["k_of_committed"].split("/")[0])))


def false_consensus(V, G):
    n_fc = 0
    for row, g in zip(V, G):
        votes = Counter(v for v in row if v in COMMITTED)
        if not votes:
            continue
        (top, k), m = votes.most_common(1)[0], sum(votes.values())
        if k >= math.ceil(0.8 * m) and top != g:
            n_fc += 1
    return n_fc / len(V)


# ---------- per condition ----------
def condition_metrics(rows, items, judges, cond, best_judge, rng):
    V, C, E, G = _matrices(rows, items, judges, cond)
    M = rho_matrix(C, E)
    rb = rho_bar(M)
    n = len(judges)
    boot = []
    for _ in range(N_BOOT):
        s = rng.integers(0, len(items), len(items))
        boot.append(n_eff(n, rho_bar(rho_matrix(C[s], E[s]))))
    pv, decided, correct = _panel(V, G)
    acc = correct.sum() / max(decided.sum(), 1)

    per_judge = {}
    informed = None
    if cond == "B":
        idx = {it["item_id"]: i for i, it in enumerate(items)}
        informed = np.zeros_like(C)
        for r in rows:
            if r["condition"] == "B" and r["item_id"] in idx and r["judge"] in judges:
                informed[idx[r["item_id"]], judges.index(r["judge"])] = r["informed"]
    for j, name in enumerate(judges):
        valid = V[:, j] != "PARSE_FAIL"
        com = C[:, j]
        pj = {"acc": round(float((com & ~E[:, j]).sum() / max(com.sum(), 1)), 4),
              "abstain": round(float((V[valid, j] == "NOT_ENOUGH_INFO").mean()) if valid.any() else 0, 4),
              "guess_rate": None}
        if informed is not None:
            un = ~informed[:, j] & valid
            pj["guess_rate"] = round(float(com[un].mean()), 4) if un.any() else None
            inf = informed[:, j] & com
            pj["acc_informed"] = round(float((~E[inf, j]).mean()), 4) if inf.any() else None
        per_judge[name] = pj

    # best single judge (chosen in A) scored on the items this panel decided; abstain counts as not correct
    bj = judges.index(best_judge["name"])
    bj_correct = (best_judge["V_A"][:, bj] == G) & decided
    bs_acc = bj_correct.sum() / max(decided.sum(), 1)

    pred = condorcet_prediction(V, G, rng)
    return {
        # capped at n: anti-correlated errors (rho_bar < 0) push Kish's formula above n; raw value kept
        "n_eff": round(min(n_eff(n, rb), n), 3), "n_eff_raw": round(n_eff(n, rb), 3),
        "n_eff_ci": [round(float(min(np.nanpercentile(boot, 2.5), n)), 3),
                     round(float(min(np.nanpercentile(boot, 97.5), n)), 3)],
        "rho_bar": round(rb, 4),
        "rho_matrix": [[None if np.isnan(x) else round(float(x), 4) for x in row] for row in M],
        "panel_acc": round(float(acc), 4), "panel_acc_ci": wilson(int(correct.sum()), int(decided.sum())),
        "coverage": round(float(decided.mean()), 4),
        "condorcet_pred": round(pred, 4), "condorcet_gap": round(pred - float(acc), 4),
        "best_single": {"judge": best_judge["name"], "acc_same_items": round(float(bs_acc), 4),
                        "ci": wilson(int(bj_correct.sum()), int(decided.sum()))},
        "per_judge": per_judge,
        "agreement_table": agreement_table(V, G, decided),
        "false_consensus": round(false_consensus(V, G), 4),
        "_boot": boot, "_C": C, "_E": E,
    }


def hypotheses(A, B, n, rng, n_items):
    h = {}
    h["H1"] = {"pass": A["n_eff"] <= n / 2,
               "detail": f"n_eff(A) = {A['n_eff']} vs threshold {n / 2} (of {n} judges)"}
    margin = A["panel_acc"] - A["best_single"]["acc_same_items"]
    h["H2"] = {"pass": margin <= 0.02,
               "detail": f"panel A {A['panel_acc']:.3f} vs best single {A['best_single']['acc_same_items']:.3f} (same items)"}
    # H3: paired bootstrap of the difference (same resampled items for A and B)
    diffs = []
    for _ in range(N_BOOT):
        s = rng.integers(0, n_items, n_items)
        diffs.append(min(n_eff(n, rho_bar(rho_matrix(B["_C"][s], B["_E"][s]))), n) -
                     min(n_eff(n, rho_bar(rho_matrix(A["_C"][s], A["_E"][s]))), n))
    lo, hi = float(np.nanpercentile(diffs, 2.5)), float(np.nanpercentile(diffs, 97.5))
    d = B["n_eff"] - A["n_eff"]
    status = "pass" if d >= 0.5 and lo > 0 else ("inconclusive" if d >= 0.5 else "fail")
    h["H3"] = {"pass": status == "pass", "status": status,
               "detail": f"n_eff(B) - n_eff(A) = {d:.2f}, paired 95% CI [{lo:.2f}, {hi:.2f}]"}
    h["H4"] = {"pass": B["panel_acc"] > B["best_single"]["acc_same_items"],
               "detail": f"panel B {B['panel_acc']:.3f} vs best single {B['best_single']['acc_same_items']:.3f} (items B decided)"}
    for k in ("H1", "H2", "H4"):
        h[k]["status"] = "pass" if h[k]["pass"] else "fail"
    return h


def compute(rows, items, judges, provider):
    rng = np.random.default_rng(config.SEED)
    VA, CA, EA, _ = _matrices(rows, items, judges, "A")
    accA = [(CA[:, j] & ~EA[:, j]).sum() / max(CA[:, j].sum(), 1) for j in range(len(judges))]
    best = {"name": judges[int(np.argmax(accA))], "V_A": VA}
    A = condition_metrics(rows, items, judges, "A", best, rng)
    B = condition_metrics(rows, items, judges, "B", best, rng)
    hyp = hypotheses(A, B, len(judges), rng, len(items))
    for c in (A, B):
        for k in ("_boot", "_C", "_E"):
            c.pop(k)
    return {
        "meta": {"n_items": len(items), "judges": judges, "n_judges": len(judges), "r": config.R,
                 "seed": config.SEED, "provider": provider, "FAKE": provider != "tokenrouter",
                 "parse_fail": {c: sum(r["verdict"] == "PARSE_FAIL" for r in rows if r["condition"] == c) for c in "AB"},
                 "generated_at": dt.datetime.now().isoformat(timespec="seconds")},
        "conditions": {"A": A, "B": B},
        "hypotheses": hyp,
    }


def main():
    with open(config.RESULTS_PATH) as f:
        rows = [json.loads(l) for l in f]
    ids = {r["item_id"] for r in rows}
    with open(config.ITEMS_PATH) as f:
        items = [it for it in map(json.loads, f) if it["item_id"] in ids]
    judges = [j for j in config.JUDGES if any(r["judge"] == j for r in rows)]
    meta_path = config.RESULTS_PATH.parent / "run_meta.json"
    provider = json.loads(meta_path.read_text())["provider"] if meta_path.exists() else "unknown"
    m = compute(rows, items, judges, provider)
    config.METRICS_PATH.write_text(json.dumps(m, indent=1))
    A, B = m["conditions"]["A"], m["conditions"]["B"]
    print(f"[{provider}] N={len(items)} judges={len(judges)}")
    for c, x in (("A", A), ("B", B)):
        print(f"  {c}: n_eff={x['n_eff']} {x['n_eff_ci']} rho_bar={x['rho_bar']} panel_acc={x['panel_acc']} "
              f"cov={x['coverage']} best_single={x['best_single']['acc_same_items']} gap={x['condorcet_gap']}")
    for k, v in m["hypotheses"].items():
        print(f"  {k}: {v['status'].upper():12s} {v['detail']}")


if __name__ == "__main__":
    main()
