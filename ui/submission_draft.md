# Condorcet Agent — corrected submission draft

## Approach

Condorcet turns Ezio's claim verdicts, sources, scores, and findings into a traceable next action and a targeted question for an accountable human. It groups listed sources by origin, excludes sources predating the claim period, separates hard-rule warnings from exposure-associated split evidence, and compares the panel's action with a simple rule. The corrected historical EV experiment yields STABLE/REWRITE in both conditions; the five models common to the two valid panels give identical votes, so we do not claim that hiding evidence improves decisions.

## Short pitch

An AI answer can sound confident while its evidence is weak. Condorcet shows what to do next, why, and who should check it. The EV example exposes a mismatch between Ezio's verdict and its own quoted figure, and the human update is recorded without removing the safety floor. On Nuclear, six source entries become three usable origin groups, so the next action is to find another source. Our judge table makes evidence exposure and citations visible. We exclude malformed votes, compare against a simple rule, and report that our historical real-model comparison does not prove a benefit from evidence subspaces. A decision holding up is not proof that it is correct.

## Tools used and reuse

Claude contributed earlier backend work; Codex reviewed and corrected the backend, built and verified the UI, and produced the video. The default demo and human reruns use deterministic simulated judges. TokenRouter supplied historical real-model experiments; these structured votes were locally revalidated, with original raw replies unavailable and no new inference prompts in the correction pass. Ezio inputs were transcribed from screens because no PDF export was available, with approximate-score limitations disclosed. The morning's small balanced-partition and n_eff utilities were reused as documented. Buddy artwork is reused unchanged from the user's MockingIt project and remains optional. Windows SAPI supplies synthetic narration, and Pillow/FFmpeg assemble the screenshot walkthrough.

## Assets

- Video: `ui/video/condorcet_demo_corrected.mp4` (1:48, EV plus Nuclear, synthetic narration and saved screenshot states disclosed).
- Captions: `ui/video/condorcet_demo_corrected.srt`.
- Repository: https://github.com/harshilmehta1512/condorcet-agent.
- UI: `python -m streamlit run ui/app.py`.
- Validation: 26 passing checks; all four reports and both real-model variants render.
- Details and limitations: `docs/07_SUBMISSION_READY.md`.

The old video files and experiment claims are historical and superseded. This draft does not imply that a buildathon submission has been performed.
