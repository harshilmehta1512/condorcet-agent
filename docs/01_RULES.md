# 01 — Project Rules (Condorcet Agent, Build a Trust Agent track; LOCKED 1:46 PM)

## A. Event rules (from the official challenge page)
1. Challenge work happens from 1:15 PM PT; **organizers extended the deadline to 3:45 PM** (confirmed by the team at 2:27). Starters, general libraries, APIs and boilerplate are allowed; a pre-built solution to the challenge isn't.
2. **Reuse of morning code:** only small general statistics utilities (balanced evidence partition, n_eff formula). Everything challenge-specific is written in the window. **Disclose the reuse in the tools-used note.** If unsure, ask a mentor.
3. Inputs are the **Ezio sample reports** (ezioai.io → Try Product → code `EZIOHACK2026`), exported as PDFs.
4. The agent must work on **any** of the 4 reports. The video shows the main report **and** one other with a different, sensible decision. **A one-report demo isn't scored.**
5. Use only the sample reports; no confidential or personal data.
6. Submission: 1–2 min demo video, repo link, short approach description, tools-used note (which AI/event tools and how), optional Best Use of Ezio note.

## B. Cost
1. **No personal money.** LLM calls use event TokenRouter credits only. Keys in `.env` (gitignored).
2. Cache every LLM response on disk by request hash; re-runs never pay twice.
3. `--offline` mode (deterministic mock panel) must always work, so the demo can't fail.

## C. Honesty
1. Say "the decision **holds up** across evidence views," never "the decision is correct."
2. Never claim repeated sources we didn't observe in the real reports.
3. Every reason cites evidence ids (claim, source, score, finding).
4. **Code sets the safety floor; LLM judges can only make the decision stricter.**
5. Never hand-edit parsed JSON or decisions. Fix the code.
6. Cite: Kohli 2026, Kim et al. 2025, Ho 1998, Breiman 2001, Dong et al. 2009, Kish.

## D. Engineering
1. Python 3.9+, `pypdf` for parsing, `httpx` for TokenRouter, Streamlit for the UI.
2. Locked contracts: `parsed/<name>.json`, `decisions/<name>.json` (see `03`). The UI reads only these.
3. Deterministic: same report + context + human answer → same decision (temperature 0, seed 42, cache).
4. After every policy change, run all 4 reports.

## E. Time
1. **Feature freeze 3:15 PM.** 3:15–3:35: record the video (≤ 2 takes). 3:35: submit (deadline 3:45).
2. Cut order if late: n_eff display → flip-evidence visual polish → number of judges (9 → 5). **Never cut:** the second report, the human loop, the hard-rule floor.

## F. Documentation
1. Update `05_PROJECT_LOG.md` after every completed task.
2. Every threshold has a one-line reason in `03`.
