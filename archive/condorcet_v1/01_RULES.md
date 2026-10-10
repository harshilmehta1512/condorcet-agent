# 01 — Project Rules (Condorcet)

These rules apply to everyone on the team for the whole build (Oct 10, 2026, 1:15–3:00 PM PT). If a rule blocks progress, change it in this file and log the change in `05_PROJECT_LOG.md`. Don't quietly ignore it.

## A. Cost and access
1. **No personal money is spent.** API calls go only through event-provided credits (TokenRouter). If credits run out, stop and switch to fallback mode (rule D4). Never use a personal API key.
2. **Cache every model response** on disk, keyed by `(model, prompt_hash)`. Never pay twice for the same call. Re-running analysis must never re-call models.
3. **Pilot before full run.** Run 20 items first. Do the full run only if ≥95% of responses parse and every judge responds.

## B. Scientific honesty
1. **Ground truth comes from humans only.** All correctness is judged against SciFact's human labels and human-annotated evidence sentences. **An LLM never grades an LLM.**
2. **Hypotheses are pre-registered** in `02_PROBLEM_STATEMENT.md` before any real data is seen. Don't edit them after results arrive. If one fails, report it as failed.
3. **Never type a number into slides or the UI by hand.** Every number shown comes from `results/metrics.json`, which is generated from `results/results.jsonl`.
4. **Never edit `results.jsonl` by hand.** Fix the code and regenerate it, then log the bug.
5. **Always show uncertainty.** Accuracies get 95% Wilson intervals; n_eff gets a bootstrap 95% interval. Say "N = X" on every chart.
6. **Cite what we build on.** Kohli 2026 (problem), Kim et al. 2025 (correlated errors), Breiman 2001 and Ho 1998 (method), Wadden et al. 2020 (dataset). We claim only the evidence-partitioning hypothesis and the tool as ours.
7. **Use "test", not "prove".** We test hypotheses. A negative result for Part 2 still gets presented, honestly.

## C. Engineering
1. **Interfaces are locked.** The three data contracts in `03_architectural_flow.md` (`items.jsonl`, `results.jsonl`, `metrics.json`) don't change without both people agreeing. Log every change.
2. **Fixed random seed = 42** everywhere: item sampling, evidence partitioning, bootstrap, simulation.
3. **Temperature = 0** for every judge, where the model allows it. Log any model that doesn't.
4. **One judge = one model.** At most 2 judges from the same model family.
5. **Parse failures:** retry once. If it still fails, record `verdict = "PARSE_FAIL"`. These are excluded from metrics but reported as a count.
6. **The UI is built against fake data first** (`scripts/make_fake_data.py`) so it never waits on the backend.
7. **Commit early, commit often**: at least after every completed task in the log.

## D. Time and scope
1. **Feature freeze at 2:40 PM.** After that: rehearsal and backup video only.
2. **Cut-down triggers:**
   - 2:05 PM and the full run isn't done → N = 60 items.
   - A model is unavailable → drop it (minimum 5 judges) and set n accordingly.
   - Condition B is broken at 2:15 → present Part 1 plus an honest note on B.
3. **Stretch goals** (only if everything works by 2:25): live single-claim run in the UI, a third condition (judges with different prompts).
4. **Fallback mode:** if no API access at all, compute Part 1 on public Open LLM Leaderboard per-item data (no API calls) and present Part 2 as the proposed experiment.

## E. Documentation
1. Update `05_PROJECT_LOG.md` **after every completed task**: move it from Running to Done, add any decision or bug, and update Next and Pending.
2. Every decision gets an ID (D1, D2, …) and a one-line reason.
3. Every bug gets an ID (B1, B2, …), a symptom, a cause and a fix.

## F. Demo
1. **The UI's default mode replays recorded results.** Live calls are optional and never the only way to demo.
2. Record a backup screen video of the full demo before 2:55 PM.
3. Check the event's rules on prepared material. Docs and plans are written ahead of time; code is written during the build.
