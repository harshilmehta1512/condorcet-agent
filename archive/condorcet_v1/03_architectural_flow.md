# 03 — Architectural Flow

## 1. System overview

```
                ┌──────────────────────────────────────────────────────────┐
                │                  BACKEND (Person 1)                      │
SciFact  ──►  [1] load_data.py ──► data/items.jsonl                       │
(S3 tarball)       │                                                      │
                   ▼                                                      │
              [2] partition.py ──► data/assignments.jsonl  (who sees what)│
                   │                                                      │
                   ▼                                                      │
              [3] run_judges.py ──► cache/  ──► results/results.jsonl     │
                   │   (async, TokenRouter, temp 0, retry, cache)         │
                   ▼                                                      │
              [4] analysis.py ──► results/metrics.json                    │
                   │                                                      │
              [5] tests/ (pytest: formulas, partition coverage, parsing)  │
                └──────────────────────────────────────────────────────────┘
                                   │  (contracts: items / results / metrics)
                                   ▼
                ┌──────────────────────────────────────────────────────────┐
                │                  FRONTEND (Person 2)                     │
                │  scripts/make_fake_data.py ──► fake items/results/metrics│
                │  app.py (Streamlit) reads the 3 files ──► 4-screen demo  │
                └──────────────────────────────────────────────────────────┘
```

**Key principle:** the backend and frontend share **only the three files**. The frontend is built on fake files in the same format from minute one, so it never waits on the backend.

## 2. Repository layout

```
stanford/
├── docs/                      # these 5 documents
├── data/
│   ├── raw/                   # SciFact tarball contents (gitignored)
│   ├── items.jsonl            # CONTRACT 1
│   └── assignments.jsonl      # evidence subsets per (item, judge)
├── cache/                     # one JSON per (model, prompt_hash) (gitignored)
├── results/
│   ├── results.jsonl          # CONTRACT 2
│   └── metrics.json           # CONTRACT 3
├── src/
│   ├── config.py              # judges, N, seed, r, paths, API base URL
│   ├── load_data.py
│   ├── partition.py
│   ├── llm_client.py          # async OpenAI-compatible client + cache + retry
│   ├── run_judges.py
│   └── analysis.py
├── scripts/make_fake_data.py
├── tests/
├── app.py                     # Streamlit UI
└── requirements.txt           # httpx/openai, numpy, pandas, scipy, streamlit, plotly, pytest
```

## 3. Data contracts (locked; rule C1)

### CONTRACT 1 — `data/items.jsonl` (one line per claim)
```json
{"item_id": 17,
 "claim": "Aspirin reduces risk of ...",
 "doc_id": 4983,
 "title": "...",
 "sentences": ["S0 text", "S1 text", "..."],
 "gold": "SUPPORT",
 "gold_idx": [2, 5]}
```
- `gold` ∈ {SUPPORT, CONTRADICT}. Claims without evidence (NOINFO) are excluded.
- `gold_idx` = human-annotated evidence sentence indices in this abstract.

### CONTRACT 2 — `results/results.jsonl` (one line per judge call)
```json
{"item_id": 17, "condition": "A", "judge": "haiku", "model": "claude-haiku-5-5",
 "shown_idx": [0,1,2,3,4,5,6,7], "informed": true,
 "verdict": "CONTRADICT", "gold": "CONTRADICT",
 "latency_ms": 812, "cached": false}
```
- `condition` ∈ {A, B}. `verdict` ∈ {SUPPORT, CONTRADICT, NOT_ENOUGH_INFO, PARSE_FAIL}.
- `informed` = `shown_idx` ∩ `gold_idx` ≠ ∅ (always true in A).

### CONTRACT 3 — `results/metrics.json`
```json
{"meta": {"n_items": 150, "judges": ["gpt-nano", "..."], "n_judges": 9, "r": 4,
          "seed": 42, "parse_fail": {"A": 0, "B": 2}, "generated_at": "..."},
 "conditions": {
   "A": {"n_eff": 2.1, "n_eff_ci": [1.7, 2.6], "rho_bar": 0.41,
         "rho_matrix": [[1.0, 0.5, "..."]],
         "panel_acc": 0.78, "panel_acc_ci": [0.71, 0.84], "coverage": 0.99,
         "condorcet_pred": 0.94, "condorcet_gap": 0.16,
         "best_single": {"judge": "sonnet", "acc_same_items": 0.80, "ci": [0.73, 0.86]},
         "per_judge": {"haiku": {"acc": 0.74, "abstain": 0.02, "guess_rate": null}},
         "agreement_table": [{"k_of_committed": "9/9", "count": 80, "acc": 0.91, "ci": [0.83, 0.95]}],
         "false_consensus": 0.06},
   "B": {"...same keys...": "..."}},
 "hypotheses": {"H1": {"pass": true, "detail": "..."}, "H2": {}, "H3": {}, "H4": {}}}
```
- `false_consensus` = share of items where ≥ ⌈0.8·committed⌉ judges agree **and** are wrong (the dangerous case).
- `guess_rate` (B only) = share of uninformed calls where the judge committed instead of abstaining.

## 4. Component decisions

| # | Component | Decision | Reason |
|---|---|---|---|
| 1 | Data source | SciFact `claims_dev.jsonl` + `corpus.jsonl` from `https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz` (link verified reachable 12:52 PM) | Dev split has public labels and evidence sentences. Verify field names on first load. |
| 2 | Item selection | Claims with evidence; first cited doc that has a label; N = 150 sampled with seed 42 (pilot 20) | Simple, reproducible |
| 3 | Partition (B) | For each item: shuffle sentence indices (seed = 42 + item_id); shuffled sentence k → judges {k mod n, …, (k+r−1) mod n}; each judge sees its sentences **in original order**; r = ⌈0.4·n⌉ | Every sentence seen by r judges, each judge ≈ 40–45% of the abstract; deterministic |
| 4 | LLM client | OpenAI-compatible chat completions via TokenRouter base URL (**verify compatibility at 1:15**); asyncio with semaphore = 16; timeout 60 s; 1 retry; temperature 0; `max_tokens` 50 | Fast, cheap, reproducible |
| 5 | Cache | `cache/{sha256(model + prompt)}.json` checked before every call | Never pay twice; re-runs are free |
| 6 | Prompt | Single template (below), JSON-only reply | One variable at a time: only evidence changes between A and B |
| 7 | Parsing | Regex for the first `SUPPORT|CONTRADICT|NOT_ENOUGH_INFO` inside JSON; else retry once; else PARSE_FAIL | Robust to chatty models |
| 8 | Panel rule | Majority of committed judges; tie / zero committed → ESCALATE | Standard; mirrors human fallback |
| 9 | Error indicator | e = 1 if committed and verdict ≠ gold; abstain is **not** an error (pairwise stats use items where both committed) | Fair under partial evidence |
| 10 | ρ | Phi coefficient between two judges' error indicators over items where both committed; skip a pair if either has zero variance (log it); ρ̄ = mean over valid pairs | Standard; matches Kish's formula |
| 11 | n_eff | n / (1 + (n−1)·ρ̄); bootstrap CI: resample items 1,000×, seed 42 | Uncertainty at N = 150 |
| 12 | Condorcet prediction | Monte Carlo 10,000 panels: each judge independently correct / wrong / abstain with its observed rates → majority-of-committed accuracy | "What if they were independent?" |
| 13 | Best single judge | Highest accuracy in condition A; scored on the items each panel decided | Fair, matched comparison |
| 14 | Agreement table | Group items by top-vote share among committed (e.g. 9/9, 8/9 …); accuracy + Wilson CI per group | Turns "k of n agreed" into a probability |
| 15 | UI | Streamlit + Plotly; replay mode by default; optional live mode for one claim | Fast to build; demo can't break |

### Judge prompt (identical in A and B; only the evidence differs)
```
You are verifying a scientific claim using ONLY the evidence sentences below.
Claim: {claim}
Evidence:
{numbered sentences, using original indices}
If the evidence supports the claim, answer SUPPORT. If it contradicts the claim, answer CONTRADICT.
If this evidence is not enough to decide, answer NOT_ENOUGH_INFO. Do not use outside knowledge.
Reply with JSON only: {"verdict": "SUPPORT" | "CONTRADICT" | "NOT_ENOUGH_INFO"}
```

### Judge roster (fill in exact TokenRouter IDs at 1:15; at most 2 per family)
| Slot | Family | Candidate | Confirmed ID |
|---|---|---|---|
| J1 | OpenAI | gpt-5.4-nano | |
| J2 | OpenAI | gpt-5.4-mini | |
| J3 | Anthropic | claude-haiku-5-5 | |
| J4 | Anthropic | claude-sonnet-5-5 | |
| J5 | Google | Gemini Flash (latest) | |
| J6 | Meta | Llama (latest small/medium) | |
| J7 | Alibaba | Qwen (latest) | |
| J8 | Mistral | Mistral (latest small) | |
| J9 | DeepSeek | DeepSeek (latest) | |

## 5. Call budget
- Pilot: 20 items × 9 judges × 2 conditions = **360 calls**
- Full: 150 × 9 × 2 = **2,700 calls** (cached; repeat runs are free)
- At semaphore 16 and ~1 s per call: ≈ 3–5 min wall time.

## 6. Tests (Person 1)
- `test_neff`: ρ = 0 → n; ρ = 1 → 1; n = 9, ρ = 0.4375 → 2.0
- `test_wilson`: 16/20 → ≈ [0.584, 0.919]
- `test_partition`: every sentence assigned to exactly r judges; deterministic with the seed; each judge non-empty
- `test_parse`: chatty outputs, code fences, lowercase → correct verdict; garbage → PARSE_FAIL
- `test_panel`: tie → ESCALATE; all abstain → ESCALATE
- `test_metrics_on_fake`: analysis runs end to end on fake data and emits every Contract 3 key

## 7. Failure modes and fallbacks
| Failure | Fallback |
|---|---|
| TokenRouter not OpenAI-compatible | Write a thin adapter in `llm_client.py` only; nothing else changes |
| A model unavailable / slow | Drop it (min 5 judges), update `config.py`, log it |
| Parse rate < 95% in pilot | Tighten prompt (rule: log as decision), re-pilot |
| Run not done by 2:05 | N = 60 |
| No API at all | Part 1 on Open LLM Leaderboard per-item data (no calls); Part 2 presented as design |
