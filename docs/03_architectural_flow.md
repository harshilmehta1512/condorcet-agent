# 03 — Architectural Flow (LOCKED 1:46 PM)

## 1. Pipeline

```
reports/<name>.pdf (Ezio export) + contexts/<ctx>.json (who relies on it, for what, stakes, accountable human)
   │
[1] agent/parse_report.py   → parsed/<name>.json                 CONTRACT 1
[2] agent/origins.py        → sources grouped by origin per claim
[3] agent/evidence.py       → evidence pieces E1..Ek (claims, scores, findings)
[4] agent/subspace.py       → each piece → R of N judges (balanced round-robin, per-report seed)
[5] agent/panel.py          → N judge calls (TokenRouter, cached) → action + cited pieces
[6] agent/stability.py      → top-action share, n_eff, flip evidence
[7] agent/policy.py         → hard-rule floor + stable/fragile → final action + traced reasons
[8] agent/human.py          → if fragile: one question on the flip evidence; --human "answer" adds evidence → re-run [4]–[7]
   │
decisions/<name>.json                                               CONTRACT 2  → UI + video
```

Entry point: `python -m agent.run --report reports/ev_market.pdf --context contexts/analyst_client_note.json [--offline] [--human "answer"]`
`--offline` uses a deterministic mock panel (no network, no cost) so the demo can never fail.

## 2. Contracts (locked)

### CONTRACT 1: `parsed/<name>.json`
```json
{"report": "ev_market", "question": "...", "analyzed_text": "...",
 "verdict": {"summary": "...", "issue_count": 3},
 "modules": {"accuracy": 3, "bias": 4, "tone": 5, "agreement": 2},
 "claims": [{"id": "C1", "text": "...", "verdict": "Supported",
             "sources": [{"id": "S1", "type": "News", "title": "...", "date": "2026-03-02", "outlet": "..."}]}],
 "findings": [{"id": "F1", "category": "Factual claims", "severity": "CRITICAL", "text": "..."}]}
```

### CONTRACT 2: `decisions/<name>.json`
```json
{"report": "ev_market",
 "context": {"role": "Analyst", "use": "client note", "stakes": "high", "accountable": "Research lead"},
 "action": "ESCALATE", "status": "STABLE | INFO_GAP | FRAGILE",
 "baseline": {"action": "BLOCK", "focus": "C1", "rule": "a claim Ezio marked contradicted"},
 "panel_adds": {"value": false, "detail": "same action and focus as the simple rule"},
 "headline": "Decision depends on C3, which rests on one origin; asking the research lead.",
 "evidence": [{"id": "E3", "kind": "claim", "ref": "C3", "summary": "...", "n_sources": 4, "n_origins": 1}],
 "panel": {"n_judges": 9, "r": 4,
           "votes": [{"judge": "haiku", "model": "...", "saw": ["E1", "E3"], "action": "ESCALATE", "cited": ["E3"], "why": "..."}],
           "tally": {"ESCALATE": 5, "APPROVE": 4}, "top_share": 0.56, "n_eff": 2.3},
 "flip_evidence": {"id": "E3", "saw_it": {"ESCALATE": 4, "APPROVE": 0}, "didnt": {"ESCALATE": 1, "APPROVE": 4}},
 "hard_rules": [{"rule": "contradicted load-bearing claim → never APPROVE", "triggered": false}],
 "reasons": [{"text": "...", "evidence": ["E3", "C3", "S1-S4"]}],
 "unchecked": ["statements Ezio did not analyze"],
 "human": {"to": "Research lead", "question": "...", "answer": null},
 "before": null,
 "trace": ["..."]}
```
After `--human`, `before` holds the previous action/status/tally so the UI can show before → after.

## 3. Component rules

| # | Component | Rule | Reason |
|---|---|---|---|
| 1 | Origins | Same origin if: same outlet, **or** title token-Jaccard ≥ 0.6, **or** same date ±1 day and Jaccard ≥ 0.4 | Transparent copy/syndication detection (Dong et al. idea, simplified) |
| 2 | Evidence pieces | One per claim (with grouped sources), one "module scores", one per finding | Units a judge can see or not see |
| 3 | Subspaces | Each piece → R = ⌈0.4·N⌉ judges (N = 9 → 4), balanced round-robin + per-report random judge order (seed 42); every judge always sees the question, context and analyzed text | Random subspace method; every piece seen by several judges |
| 4 | Judge prompt | Context + the evidence pieces it was given → JSON `{action, cited:[ids], why}`; must cite only pieces it saw | Traceable votes |
| 5 | Panel roster | 9 models, ≥ 5 families (fill from TokenRouter); temperature 0; cache by hash | Independence across families; reproducible |
| 6 | Stability | STABLE if top action share ≥ 0.70; INFO_GAP if the split is explained by exposure to one piece (judges who saw it ≥ 80% agree AND judges who didn't ≥ 80% agree) → follow the judges who saw it; else FRAGILE | A split we created by hiding evidence is not uncertainty (external review, D22) |
| 6b | Baseline | `rule_baseline`: contradicted claim → BLOCK (high stakes) / REWRITE; CRITICAL finding → REWRITE; unverified → ESCALATE / PULL_SOURCE; else APPROVE. Output `baseline` + `panel_adds {value, detail}` | Every claim of panel value is checked against the obvious alternative |
| 7 | n_eff | Kish with ρ̄ = mean pairwise agreement correlation of judges' action indicators across this report's re-runs (with one report, report vote-agreement instead and label it) | Honest about the small panel |
| 8 | Flip evidence | For each piece: action distribution among judges who saw it vs didn't; pick the piece with the largest total-variation distance | "Which evidence the decision depends on" |
| 9 | Hard floor | Load-bearing contradicted claim → never APPROVE; CRITICAL finding → never APPROVE without human | Safety floor in code; LLMs can only be stricter |
| 10 | Final action | STABLE → top action (after floor). FRAGILE → ESCALATE to the accountable human with one question about the flip evidence (high stakes) or REWRITE that sentence (low stakes) | Human where it matters |
| 11 | Human answer | Answer becomes a new evidence piece "H1: <role> says …" shown to **all** judges in the re-run | Decision updates visibly |
| 12 | Offline mock | Deterministic judges: vote from rules over the pieces they saw (contradicted → BLOCK, unverified/thin → ESCALATE, else APPROVE) | Demo never depends on network |

## 4. Repo layout
```
agent/   parse_report.py origins.py evidence.py subspace.py panel.py stability.py policy.py human.py llm.py run.py
contexts/ comms_publish.json analyst_client_note.json policy_brief.json
reports/ *.pdf   parsed/   decisions/   cache/   ui/ (teammate)   docs/   archive/condorcet_v1 (morning code; see D7)
```

## 5. Budget
9 judge calls per run × 4 reports + re-runs ≈ 100–150 calls total on event TokenRouter credits; cached.
