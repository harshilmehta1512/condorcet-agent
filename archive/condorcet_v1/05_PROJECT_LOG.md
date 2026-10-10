# 05 — Project Log (decisions, bugs, tasks)

**Update after every completed task** (rule E1). Move the task from Running to Done, add any decision or bug, then refresh Next and Pending.
Last updated: **1:12 PM PT**. Backend pipeline built and tested end to end on the offline mock; waiting on the TokenRouter key for real runs.

---

## 1. Team split

| Person | Owns | Never touches |
|---|---|---|
| **P1 — Backend & testing** | `src/*`, `tests/*`, data download, judge runs, `metrics.json`, hypothesis results | `app.py` |
| **P2 — UI & frontend** | `app.py`, `scripts/make_fake_data.py`, charts, slides, demo script, backup video | `src/*` (reads outputs only) |

**Shared:** the three contracts in `03_architectural_flow.md`, this log, and the checkpoints below.

**Sync checkpoints (5 min each, both people):**
- **1:35 PM (contract check):** P1 shows a real `items.jsonl` line and a pilot `results.jsonl` line; P2 confirms the UI parses them.
- **2:05 PM (integration):** P2 switches the UI from fake to real files.
- **2:25 PM (results lock):** both read `metrics.json`; P2 puts real numbers in the slides; decide what H3/H4 say.
- **2:40 PM (freeze):** rehearsal starts.

---

## 2. Task board

### ▶ Running now
| ID | Task | Owner | Started |
|---|---|---|---|
| T0 | Get TokenRouter key → `export TOKENROUTER_BASE_URL=... TOKENROUTER_API_KEY=...` → run `python -m src.check_models` → put confirmed IDs in `src/config.py` JUDGES | P1 | 12:55 |

### ⏭ Next (start at 1:15)
| ID | Task | Owner | Target done |
|---|---|---|---|
| T3 | `scripts/make_fake_data.py` + placeholder `metrics.json` (`FAKE: true`) | P2 | 1:30 |
| T4 | `app.py` skeleton: sidebar, 4 tabs, loads the 3 files, FAKE banner | P2 | 1:40 |

### 📋 Pending (in order)
| ID | Task | Owner | Target done | Depends on |
|---|---|---|---|---|
| T6 | **Pilot run**: `CONDORCET_PROVIDER=tokenrouter python -m src.run_judges --pilot` then `python -m src.analysis`; parse rate ≥ 95% | P1 | 1:45 | T0 |
| T7 | Checkpoint 1:35: contract check | Both | 1:35 | T2, T3 |
| T8 | Tabs 1–3: claim view, judge-card grid, assignment heatmap, verdict banners | P2 | 2:05 | T4 |
| T11 | **Full run**: `CONDORCET_PROVIDER=tokenrouter python -m src.run_judges` (pilot calls are cached and reused); cut-down at 2:05 → `--n 60` | P1 | 2:05 | T6 |
| T12 | Tab 4: KPI tiles, heatmaps, n_eff curve, agreement table, hypothesis scorecard, trust calculator | P2 | 2:20 | T8 |
| T13 | Checkpoint 2:05: switch UI to real data | Both | 2:10 | T11, T9 |
| T14 | Run `analysis.py` on real results → `metrics.json`; fill H1–H4 | P1 | 2:20 | T11 |
| T15 | Find a "false-consensus example" item for the demo (A unanimous and wrong) | P1 | 2:25 | T14 |
| T16 | Slides (5 max): problem → evidence → method → results → trust calculator; real numbers only | P2 | 2:35 | T14 |
| T17 | Stretch: live single-claim run button in UI | P1 + P2 | 2:35 | T13 |
| T18 | Stretch: condition C (same evidence, diverse prompts) as a control | P1 | 2:35 | T11 |
| T19 | **Freeze**, rehearse ×2, record backup video | Both | 2:55 | — |

---

## 3. Decisions

| ID | Time | Decision | Reason |
|---|---|---|---|
| D1 | 12:30 | Project = Condorcet (judge-panel independence) | All morning tests showed frontier models catch hand-built traps; this project uses naturally occurring errors from published-scale phenomena |
| D2 | 12:40 | Dataset = SciFact dev | Human labels + human evidence sentences let us score partial-evidence judges fairly |
| D3 | 12:50 | 9 judges (min 5), at most 2 per family | Mirrors Kohli 2026; family diversity |
| D4 | 12:50 | r = ⌈0.4·n⌉ (n = 9 → r = 4) | Keeps each judge at about 40–45% of the evidence, same as the original 5-judge design |
| D5 | 12:50 | Pre-registered H1–H4 (see `02_PROBLEM_STATEMENT.md` §4) | Prevents moving the goalposts after seeing results |
| D6 | 12:50 | Replay mode is the default in the UI | The demo cannot fail on a network call |
| D7 | 12:50 | Event credits only; response cache | No personal cost; re-runs are free |
| D8 | 12:55 | Track = Build Trust Agent (pending reveal) | Outputs a measured trust level for multi-agent verdicts |
| D11 | 13:05 | H3 uses a **paired** bootstrap of n_eff(B) − n_eff(A) (same resampled items for both); pass = diff ≥ 0.5 and CI lower bound > 0; diff ≥ 0.5 with CI including 0 = inconclusive | More correct than comparing two separate CIs; same spirit as 02 §4 (wording there unchanged per rule B2) |
| D12 | 13:06 | n_eff reported capped at n; uncapped value kept as `n_eff_raw` (extra key, contract otherwise unchanged) | Negative ρ̄ (anti-correlated errors) pushes Kish's formula above n, which would confuse the UI |
| D13 | 13:08 | Partition = balanced round-robin over r·n_s slots with a per-item random judge permutation | Fixes B2; every sentence → r distinct judges, judge loads differ ≤ 1 |
| D14 | 13:00 | Offline `mock` provider is the default (`CONDORCET_PROVIDER`); metrics from mock runs are flagged `meta.FAKE = true` | Build and test the whole pipeline at zero cost; mock numbers can never be mistaken for results |
| D15 | 13:02 | Items: SciFact dev, first cited doc with one consistent label; 188 eligible → 150 sampled (seed 42): **100 SUPPORT / 50 CONTRADICT** | Gold must be unambiguous. Note: a judge that always says SUPPORT scores 67%, so read per-judge accuracy against that baseline |
| D16 | 13:10 | Client reads only `TOKENROUTER_*` env vars, never `OPENAI_API_KEY` | Enforces rule A1 (no personal spend) in code |
| D9 | 13:00 | Fake data lives in `fake/` (`fake/items.jsonl`, `fake/results.jsonl`, `fake/metrics.json`); real data stays in `data/` and `results/` | Fake data can never overwrite real results; UI switches with one sidebar toggle |
| D10 | 13:00 | Live-run interface for the UI stretch goal: P1 will expose `src.run_judges.run_single(item_id) -> list[dict]` returning Contract 2 rows | UI can wire the button against a stub before the backend exists |

## 4. Bugs

| ID | Time | Symptom | Cause | Fix | Status |
|---|---|---|---|---|---|
| B1 | 13:03 | `analysis.py` crashed: "Probabilities are not non-negative" in the Condorcet simulation | 1 − p_correct − p_wrong came out as −1e-17 from float rounding | Clip to ≥ 0 and renormalise | Fixed |
| B2 | 13:07 | `test_partition[3]` failed: judges 6–8 got no sentences on short abstracts; 26 empty subsets in B | Sentence k went to judges k..k+r−1, so high-index judges (always the same models) were starved when n_s < n | Balanced round-robin + per-item judge permutation (D13); 0 empty subsets now | Fixed |
| B3 | 13:09 | H3 paired CI [6.83, 17.03] didn't contain the point estimate 6.55 | Bootstrap diffs used uncapped n_eff while the point estimate was capped | Cap inside the bootstrap too | Fixed |

## 5. Done
| ID | Task | Owner | Finished |
|---|---|---|---|
| T-docs | Created docs 01–05 | Claude | 12:55 |
| T1 | `src/config.py`, `src/llm_client.py` (async, cache, 1 retry, temp 0, mock provider), `src/check_models.py` | P1 | 13:10 |
| T2 | `src/load_data.py` → `data/items.jsonl` (150 items) | P1 | 13:02 |
| T5 | `src/partition.py` → `data/assignments.jsonl` (2,700 rows, 0 empty, B informed share 0.62) | P1 | 13:08 |
| T9 | `src/analysis.py` → `results/metrics.json` (all Contract 3 keys + H1–H4) | P1 | 13:06 |
| T10 | `tests/test_backend.py`: 18 tests passing (neff, wilson, partition ×4, parse ×8, prompt, panel, rho, contract keys) | P1 | 13:11 |
| T-mock | Full pipeline run on the offline mock (150 × 9 × 2): works end to end; numbers are FAKE by construction | P1 | 13:11 |
