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

## Real AI judges (TokenRouter)
Put `TOKENROUTER_BASE_URL` and `TOKENROUTER_API_KEY` in `.env` (never committed), then:
```bash
.venv/bin/python -m agent.check_models --list      # free: available model IDs
.venv/bin/python -m agent.check_models             # 1 tiny call per judge
.venv/bin/python -m agent.run --report parsed/ev_market.json --context contexts/analyst_client_note.json --dry-run
.venv/bin/python -m agent.run --report parsed/ev_market.json --context contexts/analyst_client_note.json
```

## Inputs
The four Ezio sample reports (ezioai.io → Try Product) had no PDF export, so they were transcribed from screenshots into `parsed/*.json` (structured) and `reports/*.txt|.pdf` (readable). Each file's `source_note` says so.

## Note
`archive/condorcet_v1/` holds our earlier judge-panel experiment from this morning (not used by the agent; the agent reuses only its small balanced-partition and n_eff utilities, disclosed in the submission).
