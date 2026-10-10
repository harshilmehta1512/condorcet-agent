# Condorcet Agent: a trust agent that counts independent evidence

**Track:** Build a Trust Agent (Ezio Decision-Grade AI buildathon, Oct 10, 2026)

The agent reads an Ezio trust report and decides what happens next: APPROVE, REWRITE, PULL_SOURCE, ESCALATE or BLOCK.
- **Source independence:** per claim, sources published before the claim's period ended are dropped and the rest are grouped by shared origin ("6 sources → 3 independent").
- **Evidence-subspace panel:** 9 judges each see a different slice of the evidence (random subspace method). If ≥ 70% agree the decision is STABLE; otherwise it is FRAGILE and the agent finds the evidence the decision depends on.
- **Human in the loop:** one targeted question to the accountable person; the answer is added as evidence and the decision re-runs (before → after).
- **Safety floor in code:** a contradicted claim or a CRITICAL finding can never be approved.

Background and design: `docs/02_PROBLEM_STATEMENT.md`, `docs/03_architectural_flow.md`. Decisions and bugs: `docs/05_PROJECT_LOG.md`.

## Setup
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Run (offline, simulated judges, no API key needed)
```bash
.venv/bin/python -m agent.run --report parsed/ev_market.json --context contexts/analyst_client_note.json --offline
.venv/bin/python -m agent.run --report parsed/ev_market.json --context contexts/analyst_client_note.json --offline \
    --human "Confirmed from Geely's 2024 annual report: 1.49 million."
```
Other reports: `parsed/nuclear.json` (+ `contexts/policy_brief.json`), `parsed/work_from_home.json` (+ `contexts/comms_publish.json`), `parsed/agi_timelines.json` (+ `contexts/strategy_memo.json`).
Output: `decisions/<report>.json` (contract in `docs/03_architectural_flow.md` §2), read by the UI.

## Evidence workspace (Streamlit)

On Windows, run `start-ui.cmd`, or:

```powershell
.\.venv\Scripts\python.exe -m streamlit run ui/app.py
```

The workspace shows all four reports, source-origin trails, the judge exposure/citation grid, a simple-rule comparison, saved before/after states, a human answer form, reasons, limitations, and downloadable decision JSON. Missing artifacts show a helpful message. Judges in the saved files are explicitly labeled **simulated judges (rule-based)**.

Buddy is an optional text-only companion using the user's MockingIt character. Guided review records four inspection steps without changing the decision. Live UI answers are local simulations isolated under ignored `cache/ui-reviews/`; saved demo decisions remain intact.

See `docs/06_CODEX_REVIEW.md` for current findings, fixes, and remaining limitations. PDF parsing is not implemented; use the supplied `parsed/*.json` inputs. Run checks with `.\.venv\Scripts\python.exe -m pytest tests -q`.

## Real AI judges (TokenRouter)
Put `TOKENROUTER_BASE_URL` and `TOKENROUTER_API_KEY` in `.env` (never committed), then:

The provider-qualified judge roster is confirmed in the current catalog. Model listing does not run judge prompts. Missing live configuration produces an error; `--offline` explicitly selects simulation.
```bash
.venv/bin/python -m agent.check_models --list      # free: available model IDs
.venv/bin/python -m agent.check_models             # 1 tiny call per judge
.venv/bin/python -m agent.run --report parsed/ev_market.json --context contexts/analyst_client_note.json --dry-run
.venv/bin/python -m agent.run --report parsed/ev_market.json --context contexts/analyst_client_note.json
```

## Corrected demo and historical real-model comparison

Use `ui/video/condorcet_demo_corrected.mp4` with its `.srt` captions. This is a short narrated walkthrough of real UI screenshots and saved results, with synthetic narration disclosed.

`docs/07_SUBMISSION_READY.md` contains the current fixes, results, reproduction steps, and submission disclosure. `scripts/regenerate_submission.py` regenerates the four simulated reports and human snapshots, and revalidates the supplied historical TokenRouter votes without inference calls. It preserves original experiment artifacts and records the raw-response-cache limitation.

Corrected real-model results are STABLE/REWRITE in both conditions: 4/5 subspace votes and 6/7 full-evidence votes. The five common models give identical votes. A superiority claim for hiding evidence is unsupported.

## Inputs and provenance
The four Ezio sample reports (ezioai.io → Try Product) had no PDF export, so they were transcribed from screenshots into `parsed/*.json` (structured) and `reports/*.txt|.pdf` (readable). Each file's `source_note` says so.

## Note
`archive/condorcet_v1/` holds our earlier judge-panel experiment from this morning (not used by the agent; the agent reuses only its small balanced-partition and n_eff utilities, disclosed in the submission).
