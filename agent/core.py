"""Origins, evidence pieces, subspaces, stability, flip evidence and the decision policy (docs/03 §3)."""
import math
import random
import re
from collections import Counter

ACTIONS = ("APPROVE", "REWRITE", "PULL_SOURCE", "ESCALATE", "BLOCK")
STRICTNESS = {a: i for i, a in enumerate(ACTIONS)}  # higher = stricter
STABLE_SHARE = 0.70
SEED = 42
_STOP = set("the a an of and or to in on for with by at from is are was were be as that this its it new".split())


# ---------- [2] origins ----------
def _tokens(s):
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in _STOP}


def _jaccard(a, b):
    a, b = _tokens(a), _tokens(b)
    return len(a & b) / len(a | b) if a | b else 0.0


def _days(d1, d2):
    try:
        y1, m1, a1 = map(int, d1[:10].split("-"))
        y2, m2, a2 = map(int, d2[:10].split("-"))
        return abs((y1 * 372 + m1 * 31 + a1) - (y2 * 372 + m2 * 31 + a2))
    except (ValueError, AttributeError, TypeError):
        return None


def same_origin(s, t):
    """Rule from docs/03 §3 row 1. Returns the reason string, or None."""
    if s.get("outlet") and s.get("outlet", "").lower() == t.get("outlet", "").lower():
        return "same outlet"
    j = _jaccard(s.get("title"), t.get("title"))
    if j >= 0.6:
        return f"near-identical titles ({j:.2f})"
    d = _days(s.get("date"), t.get("date"))
    if d is not None and d <= 1 and j >= 0.3:
        return f"same story, same day ({j:.2f})"
    return None


def group_origins(sources):
    """Union-find over the same_origin relation -> list of {ids, why}."""
    parent = list(range(len(sources)))
    why = {}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(sources)):
        for k in range(i + 1, len(sources)):
            r = same_origin(sources[i], sources[k])
            if r:
                a, b = find(i), find(k)
                if a != b:
                    parent[b] = a
                why.setdefault(find(i), set()).add(r)
    groups = {}
    for i, s in enumerate(sources):
        groups.setdefault(find(i), []).append(s["id"])
    return [{"ids": ids, "why": sorted(why.get(root, []))} for root, ids in groups.items()]


# ---------- [3] evidence pieces ----------
def predates(claim_text, source):
    """A source published before the claim's period ended can't confirm it (observed in real Ezio reports)."""
    years = [int(y) for y in re.findall(r"\b(20[0-3]\d)\b", claim_text)]
    d = (source.get("date") or "")[:10]
    return bool(years and d and d < f"{max(years) + 1}-01-01")


def build_evidence(parsed):
    pieces = []
    for c in parsed["claims"]:
        valid = [s for s in c.get("sources", []) if not predates(c["text"], s)]
        early = [s["id"] for s in c.get("sources", []) if predates(c["text"], s)]
        origins = group_origins(valid)
        pieces.append({"id": f"E{len(pieces) + 1}", "kind": "claim", "ref": c["id"],
                       "summary": f'{c["id"]} ({c["verdict"]}): {c["text"]}', "verdict": c["verdict"], "text": c["text"],
                       "n_sources": len(c.get("sources", [])), "n_origins": len(origins), "origins": origins, "predating": early,
                       "sources": c.get("sources", [])})
    m = parsed.get("modules", {})
    pieces.append({"id": f"E{len(pieces) + 1}", "kind": "scores", "ref": "modules",
                   "summary": "Module scores (of 5): " + ", ".join(f"{k} {v}" for k, v in m.items())})
    for f in parsed.get("findings", []):
        pieces.append({"id": f"E{len(pieces) + 1}", "kind": "finding", "ref": f["id"], "severity": f["severity"],
                       "summary": f'{f["id"]} [{f["severity"]}] {f["category"]}: {f["text"]}'})
    return pieces


def evidence_text(p):
    if p["kind"] != "claim":
        return p["summary"]
    src = "; ".join(f'{s["type"]}: "{s["title"]}" ({s.get("outlet") or "?"}, {s.get("date") or "no date"})'
                    for s in p["sources"]) or "no sources"
    pre = f', {len(p["predating"])} published before the period the claim covers' if p.get("predating") else ""
    return f'{p["summary"]}\n   sources ({p["n_sources"]} listed, {p["n_origins"]} independent origin(s) that could confirm it{pre}): {src}'


# ---------- [4] subspaces (morning utility, reused per D7) ----------
def assign(n_items, n_judges, r, seed):
    """Balanced round-robin: each item -> r distinct judges; loads differ by <= 1; per-call random order."""
    rng = random.Random(seed)
    order = list(range(n_items))
    rng.shuffle(order)
    perm = list(range(n_judges))
    rng.shuffle(perm)
    shown = [[] for _ in range(n_judges)]
    for k, item in enumerate(order):
        for j in range(r):
            shown[perm[(k * r + j) % n_judges]].append(item)
    return [sorted(s) for s in shown]


def subspaces(pieces, judges, seed=SEED, always=()):
    r = math.ceil(0.4 * len(judges))
    shown = assign(len(pieces), len(judges), r, seed)
    return {j: [pieces[i]["id"] for i in idx] + list(always) for j, idx in zip(judges, shown)}, r


# ---------- [6] stability ----------
def n_eff(n, rho_bar):
    return n / (1 + (n - 1) * rho_bar)


def tally(votes):
    return Counter(v["action"] for v in votes)


def flip_evidence(votes, pieces):
    """Piece whose presence best separates the judges' actions (total-variation distance)."""
    best = None
    # Only pieces some judge actually cited: co-occurrence alone can blame a piece nobody used (bug B1).
    cited = {c for v in votes for c in v.get("cited", [])}
    for p in [p for p in pieces if p["id"] in cited] or pieces:
        saw = Counter(v["action"] for v in votes if p["id"] in v["saw"])
        didnt = Counter(v["action"] for v in votes if p["id"] not in v["saw"])
        if not saw or not didnt:
            continue
        ns, nd = sum(saw.values()), sum(didnt.values())
        tv = 0.5 * sum(abs(saw[a] / ns - didnt[a] / nd) for a in ACTIONS)
        if best is None or tv > best["tv"]:
            best = {"id": p["id"], "ref": p["ref"], "tv": round(tv, 3), "saw_it": dict(saw), "didnt": dict(didnt)}
    return best


# ---------- [7] policy ----------
def hard_floor(pieces, load_bearing_refs, human_overrides):
    """Code-level minimum strictness. Returns (min_action, rules list)."""
    rules = []
    contra = [p for p in pieces if p["kind"] == "claim" and p["ref"] in load_bearing_refs
              and re.search(r"contradict|refut|false", p["verdict"], re.I) and p["ref"] not in human_overrides]
    rules.append({"rule": "Load-bearing claim contradicted by Ezio -> never APPROVE",
                  "triggered": bool(contra), "evidence": [p["id"] for p in contra]})
    crit = [p for p in pieces if p["kind"] == "finding" and p.get("severity", "").upper() == "CRITICAL"
            and p["ref"] not in human_overrides]
    rules.append({"rule": "CRITICAL finding -> never APPROVE as is (at least REWRITE)",
                  "triggered": bool(crit), "evidence": [p["id"] for p in crit]})
    floor = "REWRITE" if (contra or crit) else "APPROVE"
    return floor, rules


def decide(votes, pieces, context, load_bearing_refs, human_overrides=()):
    t = tally(votes)
    top, k = t.most_common(1)[0]
    share = k / len(votes)
    stable = share >= STABLE_SHARE
    flip = None if stable else flip_evidence(votes, pieces)
    if stable:
        action = top
    else:
        action = "ESCALATE" if context.get("stakes", "high") == "high" else "REWRITE"
    floor, rules = hard_floor(pieces, load_bearing_refs, set(human_overrides))
    if STRICTNESS[floor] > STRICTNESS[action]:
        action = floor
    return {"action": action, "status": "STABLE" if stable else "FRAGILE", "tally": dict(t),
            "top_action": top, "top_share": round(share, 3), "flip_evidence": flip, "hard_rules": rules}
