"""Evidence subsets per (item, judge). Condition A: everything. Condition B: each sentence -> R judges."""
import json
import random

from src import config


def assign(n_sentences, item_id, n_judges=config.N_JUDGES, r=config.R, seed=config.SEED):
    """Return list (per judge) of sorted sentence indices for condition B.

    Round-robin over r*n_sentences slots: shuffled sentence k fills slots k*r .. k*r+r-1, slot t -> judge perm[t mod n].
    Every sentence reaches r distinct judges, judge loads differ by at most 1, and the judge permutation is
    re-drawn per item so no model is systematically short-changed. Deterministic per item.
    """
    rng = random.Random(seed + item_id)
    order = list(range(n_sentences))
    rng.shuffle(order)
    perm = list(range(n_judges))
    rng.shuffle(perm)
    shown = [[] for _ in range(n_judges)]
    for k, sent in enumerate(order):
        for j in range(r):
            shown[perm[(k * r + j) % n_judges]].append(sent)
    return [sorted(s) for s in shown]


def build_assignments(items, judges=tuple(config.JUDGES)):
    rows = []
    for it in items:
        n = len(it["sentences"])
        b = assign(n, it["item_id"], n_judges=len(judges))
        for j, name in enumerate(judges):
            rows.append({"item_id": it["item_id"], "condition": "A", "judge": name, "shown_idx": list(range(n))})
            rows.append({"item_id": it["item_id"], "condition": "B", "judge": name, "shown_idx": b[j]})
    return rows


def main():
    with open(config.ITEMS_PATH) as f:
        items = [json.loads(l) for l in f]
    rows = build_assignments(items)
    with open(config.ASSIGNMENTS_PATH, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    b = [r for r in rows if r["condition"] == "B"]
    gold = {it["item_id"]: set(it["gold_idx"]) for it in items}
    informed = sum(bool(set(r["shown_idx"]) & gold[r["item_id"]]) for r in b) / len(b)
    empty = sum(not r["shown_idx"] for r in b)
    print(f"wrote {len(rows)} assignments | R={config.R} | B informed share={informed:.2f} | empty B subsets={empty}")


if __name__ == "__main__":
    main()
