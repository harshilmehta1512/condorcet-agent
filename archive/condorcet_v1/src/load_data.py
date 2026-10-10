"""SciFact -> data/items.jsonl (Contract 1)."""
import json
import random

from src import config


def _read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def build_items(n_items=config.N_ITEMS, seed=config.SEED):
    corpus = {d["doc_id"]: d for d in _read_jsonl(config.RAW_DIR / "corpus.jsonl")}
    candidates = []
    for c in _read_jsonl(config.RAW_DIR / "claims_dev.jsonl"):
        # first cited doc that carries a human label (dict keys are doc_id strings)
        for doc_id in c["cited_doc_ids"]:
            sets = c["evidence"].get(str(doc_id))
            if not sets or doc_id not in corpus:
                continue
            labels = {s["label"] for s in sets}
            if len(labels) != 1:  # conflicting labels within one doc: skip, keep gold unambiguous
                continue
            doc = corpus[doc_id]
            candidates.append({
                "item_id": c["id"],
                "claim": c["claim"],
                "doc_id": doc_id,
                "title": doc["title"],
                "sentences": doc["abstract"],
                "gold": labels.pop(),
                "gold_idx": sorted({i for s in sets for i in s["sentences"]}),
            })
            break
    rng = random.Random(seed)
    rng.shuffle(candidates)
    return sorted(candidates[:n_items], key=lambda x: x["item_id"]), len(candidates)


def main():
    items, n_available = build_items()
    config.ITEMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(config.ITEMS_PATH, "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
    labels = {g: sum(it["gold"] == g for it in items) for g in ("SUPPORT", "CONTRADICT")}
    print(f"wrote {len(items)} items (of {n_available} eligible) -> {config.ITEMS_PATH} | {labels}")


if __name__ == "__main__":
    main()
