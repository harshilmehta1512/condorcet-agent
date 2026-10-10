# 05 — Project Log (Condorcet Agent, Build a Trust Agent track)

Update after every completed task (rule F1). Last updated: **2:56 PM PT**. Saved before→after snapshots for EV and AGI; human denial now reaches all judges. External-review fix (D22) shipped: INFO_GAP status + simple-rule baseline + panel-adds flag. Real-model (TokenRouter) path hardened and tested end to end against a local fake server; ready for the key. Deadline extended to **3:45** (freeze 3:15, record 3:15–3:35, submit 3:35). **All four real reports** run end to end (offline judges): EV/analyst → ESCALATE (FRAGILE→STABLE after human); Nuclear/policy brief → PULL_SOURCE (STABLE); Work-from-home/comms → ESCALATE (STABLE 9/9); AGI/board memo → ESCALATE (FRAGILE, splits on C1). Need: TokenRouter key (else label judges as simulated), repo link.

## 1. Team split
| Person | Owns |
|---|---|
| **P1 (you + Claude): backend** | `agent/*`, `contexts/*`, parsing, panel, stability, policy, human loop, running all 4 reports |
| **P2 (teammate): UI and video** | `ui/app.py`, `ui/sample_decision.json`, video, submission text |

**Sync points (revised for 3:45 deadline):** now (real `decisions/*.json` for 3 reports) · 3:00 (UI final on real data) · 3:15 (freeze, record) · 3:35 (submit).

## 2. Task board

### ▶ Running
| ID | Task | Owner |
|---|---|---|
| T1 | Generate the 4 Ezio sample reports → PDFs in `reports/` | You |
| T2 | TokenRouter key → `.env`; confirm model IDs | You |
| T3 | UI skeleton on `ui/sample_decision.json` | P2 |

### ⏭ Next
| ID | Task | Owner | Target |
|---|---|---|---|
| T5 | `parse_report.py` on the real PDFs → `parsed/*.json`; premise check on repeated sources | Claude | 2:05 |
| T6 | `llm.py` + real judge panel via TokenRouter (cached) | Claude | 2:15 |

### 📋 Pending
| ID | Task | Owner | Target |
|---|---|---|---|
| T7 | Run all 4 reports; check decisions are sensible and differ where they should | Claude + you | 2:25 |
| T8 | Human-loop demo run (`--human`) on the main report | Claude | 2:25 |
| T9 | UI on real data | P2 | 2:30 |
| T10 | Freeze, record video (main + second report) | P2 + you | 2:55 |
| T11 | Submit: video, repo, approach, tools-used note (incl. morning utility reuse, D7), Best Use of Ezio note | You | 3:00 |

## 3. Decisions
| ID | Time | Decision | Reason |
|---|---|---|---|
| D1 | 1:20 | Pivot to the **Build a Trust Agent** track | Official tracks need Ezio inputs; the morning panel experiment fit none |
| D2 | 1:22 | Morning code archived in `archive/condorcet_v1/` | Event rule: no pre-built solution |
| D3 | 1:46 | **Final design:** evidence-subspace judge panel + source-origin grouping + flip evidence → human question | Combines the morning thesis (Kohli; random subspaces) with the track's requirements |
| D4 | 1:46 | Claim is "holds up," never "correct" | No ground truth at decision time |
| D5 | 1:46 | Code sets the hard-rule floor; judges can only be stricter | Safety and traceability |
| D6 | 1:46 | `--offline` deterministic mock panel always available | Demo can't fail on network or credits |
| D7 | 1:46 | Reuse only the morning's general utilities (balanced partition, n_eff), disclosed in the tools-used note | Event allows general libraries and boilerplate; transparency |
| D8 | 1:46 | Value-of-information extension dropped | Time |
| D9 | 1:42 | Flip evidence restricted to cited pieces (B1) | Blame only evidence a judge actually used |
| D10 | 1:41 | Files consolidated: `agent/core.py` (origins, evidence, subspaces, stability, policy), `agent/panel.py` (LLM + mock judges), `agent/run.py` (entry, human loop), `agent/parse_report.py` (pending PDFs) | Faster to build than 10 small files; same steps as 03 §1 |
| D12 | 2:13 | New rule from real data: a source published **before the period a claim covers ended** can't confirm it; excluded from the independent count | Observed in the EV report: 2024 sales claim cites sources from 2010 and Jan/Feb 2024; 2024 revenue claim cites a 2022 page |
| D13 | 2:13 | Same-day story threshold lowered 0.4 → 0.3 | Real titles of one story ("annual revenue decline", 1 day apart) scored 0.33 |
| D14 | 2:14 | Flag Ezio "contradicted" verdicts whose quoted figure matches the claim | Observed: Geely 1.49M marked contradicted while Ezio's note says sources say 1.49M |
| D15 | 2:25 | **Premise confirmed on real data**: Nuclear C4 lists the same CNN article twice (6 sources → 5 origins); C5's 6 Official sources include 4 Department of Energy pages (6 → 3) | Observed in `parsed/nuclear.json` |
| D16 | 2:26 | All Ezio-extracted claims are load-bearing; CRITICAL wording findings (flattery, bias) → at least REWRITE, not ESCALATE | Ezio extracts ≤ 5 important claims; wording problems are fixed by rewriting |
| D17 | 2:28 | WFH report: C5 (the only Supported claim) lists the same Chicago Booth Review article 3× → 6 sources, 4 origins | Strongest real example of inflated support |
| D18 | 2:28 | Stable ESCALATE also gets one targeted question (most-cited evidence among escalating judges); Ezio bias ≤ 2/5 and "accuracy not scored" become reasons, and mock judges REWRITE on bias ≤ 2 | Human loop must name what to check even when judges agree; use all module signals |
| D19 | 2:30 | AGI report: C2 lists 4 sources → 1 usable origin (same WSJ article twice; 2 sources dated before 2025 ended); C4 lists the same law-journal article twice. New context `contexts/strategy_memo.json` (board memo, COO accountable) | Strongest single example for the video |
| D20 | 2:44 | Pre-flight tooling: `--dry-run` (prints the exact prompts + token estimate, sends nothing), `agent/check_models.py --list` (free model catalog) and ping (9 tiny calls), `scripts/fake_tokenrouter.py` (local fake for zero-cost wiring tests); `CONDORCET_CACHE` / `CONDORCET_OUT` isolate test runs from real results | Spend credit only after the wiring is proven |
| D21 | 2:44 | Judge prompt: "[H1] is from the accountable human; treat it as authoritative for the claim it names" | Real LLMs must weigh the human's answer correctly |
| D22 | 2:53 | **External review accepted:** "the disagreement is created by hiding evidence, and the flip evidence is what a simple rule finds." Fix: new status INFO_GAP for exposure-explained splits (decision follows the judges who saw the piece); FRAGILE only for disagreement among judges with the same evidence; every decision shows a simple-rule baseline and a `panel_adds` flag. Result with simulated judges: panel adds nothing beyond the rule on EV, WFH, AGI; differs on Nuclear (PULL_SOURCE vs REWRITE). Real-model test (full-evidence panel) pending the key | Close the loophole by claiming only what we show, against the obvious baseline |
| D23 | 2:56 | Second external review: (1) flip evidence = what the rule flags → already reported as `panel_adds: no` (D22), stays an open question until real models; (2) inputs are transcriptions → disclosed in every file, README, UI header and the video's first line; (3) saved files lacked before→after → `decisions/{ev_market,agi_timelines}.after_human.json` snapshots | Close each point with evidence in the repo |
| D11 | 1:41 | Human answer → offline keyword mapping (confirm / deny / inconclusive) onto the flip claim; shown to all judges as H1 | Deterministic, demo-safe |

## 4. Bugs
| ID | Time | Symptom | Cause | Fix | Status |
|---|---|---|---|---|---|
| B6 | 2:55 | AGI: COO says C1 is false, but the decision stayed INFO_GAP | Simulated judges ignored the human piece H1 unless they had also been shown the C1 claim piece | A denial in H1 now counts for every judge (H1 is shown to all) → AGI after: BLOCK STABLE | Fixed |
| B4 | 2:38 | A failed API call (error text) was parsed into an ESCALATE vote | `parse_vote` defaulted unparseable replies to ESCALATE, including errors | Errors are now returned separately, the judge is excluded and listed under `panel.failed`; < 5 answering judges → refuse to decide | Fixed |
| B5 | 2:41 | 3 of 9 calls failed with connection errors when all fired at once (fake server) | 9 simultaneous requests; retry logic switched to "reasoning params" on any error | Max 4 calls in flight; network/429/5xx → backoff retry; only HTTP 400 or empty reply → reasoning-model params (no temperature, max_completion_tokens 2000) | Fixed |
| B3 | 2:30 | AGI C1 wrongly flagged "Ezio contradicts its own evidence" | Number check compared the verdict's numbers against a summary string that already contained the verdict | Compare against the claim text only (new `text` field on claim pieces) | Fixed |
| B2 | 2:12 | Ezio has no PDF export button | Product only offers Copy Link / Copy Report | EV report transcribed from screenshots → `parsed/ev_market.json` + `reports/ev_market.txt/.pdf`; other reports via Copy Report paste | Workaround |
| B1 | 1:42 | Low-stakes test named the module scores as flip evidence | Flip search used co-occurrence only; by chance, judges who saw the scores didn't see C1 | Only pieces some judge actually cited are flip candidates | Fixed |

## 5. Done
| ID | Task | Finished |
|---|---|---|
| T0 | Read official track specs; cloned starter repos | 1:17 |
| T-docs | Docs 01–05 rewritten for the locked design | 1:40 |
| T13 | D22 implemented; all 4 reports + EV human loop re-run (EV: BLOCK INFO_GAP → after human: ESCALATE STABLE) | 2:53 |
| T12 | Real-model path tested end to end on fake TokenRouter: 404 model excluded, temperature-rejecting model retried, chatty JSON parsed, 2nd run 100% cached, wrong key refused, real `decisions/` untouched | 2:44 |
| T7c | AGI timelines report transcribed + run (strategy memo context); all 4 reports re-run after B3 fix | 2:31 |
| T7b | Work-from-home report transcribed + run (comms context) | 2:28 |
| T7 | Nuclear report transcribed + run with 2 contexts; decisions differ from EV | 2:26 |
| T5 | EV report transcribed + run; premise check: little exact duplication, but predating sources and a self-inconsistent verdict found (D12, D14) | 2:15 |
| T4 | Offline core + 3 contexts + synthetic test report (`contexts/_test_parsed.json`, TEST ONLY); runs high-stakes, human loop and low-stakes cases | 1:43 |
