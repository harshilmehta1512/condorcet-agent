# Latest-source review and UI delivery

This records the initial review. The pending items below were subsequently addressed in the consolidated correction pass; use `07_SUBMISSION_READY.md` for current results and limitations.

Reviewed GitHub `harshilmehta1512/condorcet-agent` at commit `97371ac` on October 10, 2026. The prior download was not a Git checkout, so the latest repository was cloned into the sibling `upstream/` directory and `git pull --ff-only` confirmed it was current. The prior download is preserved. Credentials were copied into the new checkout's ignored `.env` without printing them.

## What the upstream updates already fixed

- Saved before/after demo states for EV and AGI.
- Human denials now reach all simulated judges through H1.
- Added INFO_GAP and a simple-rule baseline so exposure-created splits and comparisons with rules are visible.

## What was still wrong, and disposition

| Priority | Location | Finding | Disposition |
| --- | --- | --- | --- |
| 1 | `agent/core.py:hard_floor` | A human confirmation removed the contradicted/critical rule trigger and could permit APPROVE. | Fixed: human statements cannot remove the hard-rule floor. Focused regression coverage added. Explicit reviewed source replacement remains a future feature. |
| 2 | `ui/app.py` | No UI existed; demo states, source trails, and judge exposure could not be inspected together. | Implemented a Streamlit evidence workspace, four reports, saved-state selector, per-claim source tables, judge matrix, human flow, reasons, limitations, trace, and JSON export. |
| 3 | `agent/panel.py:parse_vote` | Malformed or uncited model text counted as an ESCALATE vote. | Fixed: require a valid action, seen evidence citations, and a rationale; invalid responses are excluded from the panel. Provider response bodies are no longer copied into errors. |
| 4 | `agent/run.py:interpret_human` and H1 construction | Unresolved wording could match positive keywords; a response without flip evidence could cite nonexistent H1. | Fixed: explicit outcome prefixes, negation handling, validated `--human-ref`, stored target, required initial state, H1 shown to every judge. |
| 5 | `agent/core.py:decide` and generated wording | Grouping judges by exposure to one piece does not establish that they saw the same complete evidence. An 80% group threshold is not unanimity. | Corrected generated wording and UI explanations. Preserved the upstream INFO_GAP policy; controlled full-evidence/model comparisons remain pending. |
| 6 | `agent/panel.py:JUDGES` | All nine configured IDs were absent from the authenticated TokenRouter catalog checked earlier in this session (152 available IDs). | Still pending: choose supported IDs across the desired families and verify them before inference. No paid model prompts were sent during UI work. |
| 7 | `agent/core.py:flip_evidence` | EV/AGI can report the already-triggered hard-rule piece as the split-associated evidence. | UI explicitly labels this as already flagged by a rule. A separate beyond-rule search remains pending; it must not invent a flip when none exists. |
| 8 | `agent/run.py:load_parsed` | Advertised PDF input imported a nonexistent parser. | Added a clear unsupported-input error and documented JSON input. PDF parsing remains unimplemented. |
| 9 | `agent/run.py` | Implicit platform encoding risks corrupted input/output on Windows. | Explicit UTF-8 added to the active report/context/output path and UI readers. |

Screenshot provenance was already present in all four parsed inputs. `n_eff` is absent from the saved panel data; the UI hides it unless an estimate is supplied. Summed origin counts are labeled as per-claim groups, not globally unique independent sources. The UI labels offline judges as simulated (rule-based) and shows whether the panel differs from the simple baseline, including “No.”

## Gamification design

Buddy is an optional guide. It uses the user's actual MockingIt character, small idle movement, and text bubbles generated from the selected report's data. No voice or audio is used. Its focus can be changed to the decision, source independence, or the human question.

The optional four-step review progression records inspection of evidence, the panel, the human handoff, and report limits. Completing the steps earns an Evidence explorer acknowledgment. Progress is local to the session and report and has no effect on action, vote tally, or confidence. No correctness points or rewards for approval are fabricated.

Possible next iteration: a training mode with source-deduplication challenges and explanation cards, separate from real report decisions. Add expression variants for reviewing, waiting, and completion. A 3D GLB companion can follow if it helps the demo, but the existing PNG keeps this workspace lightweight.

## Validation and limits

- Twenty automated checks passed: all four reports are repeatable; cited reasons resolve; the floor survives confirmation; invalid model votes are rejected; unresolved human statements do not confirm; explicit-target H1 reaches every judge; local UI submissions preserve demo files; missing/invalid files have safe reader errors; all four UI reports render; a UI human submission succeeds.
- Streamlit starts on loopback and browser QA covers the initial decision, judge grid, source trails, Buddy, saved human states, and navigation at 1280×720.
- UI human submissions always use an isolated offline run under ignored `cache/ui-reviews/<session>/`; original demo decisions are preserved. Historical snapshots retain their original trace. They are examples, not independently verified human answers.
- This is local-only work. No deployment, GitHub push, or inference calls were made.

## AI tools used note

Codex reviewed the latest repository, implemented and checked the UI and targeted backend fixes. The existing backend/project documentation records prior Claude use. The project reuses the morning's general balanced-partition and n_eff utilities as already disclosed. The orange Buddy artwork was reused unchanged from the user's MockingIt/BuddyV Game project; CSS movement and text reveal were added. No AI image or voice generation was used for the character.
