# Condorcet Agent — submission draft

## Approach (three sentences)

Condorcet Agent turns an Ezio trust report into an action by grouping claim sources by shared origin, giving judges different evidence slices, and applying a hard-rule safety floor. It distinguishes stable votes, splits explained by evidence exposure (INFO_GAP), and disagreement within exposure groups (FRAGILE), then asks an accountable human a targeted question and shows the decision before and after their answer. Every decision exposes the simple-rule baseline and whether the panel changes its action or focus; our real-model EV control found that hiding evidence lowered agreement, so improved decision quality remains unproven.

## Original pitch from docs/02 §8 (approximately 45 seconds)

“Our trust agent reads an Ezio trust report and decides what happens next: approve, rewrite, pull another source, escalate, or block. Most agents take the report's verdict at face value. But agreement isn't proof. Recent research by Guneet Kohli shows nine AI judges agreeing carry about the information of two independent votes. So we borrowed a classic fix from random forests, the random subspace method: each judge sees a different slice of the evidence. If the decision holds no matter which evidence a judge sees, the agent acts. If it changes, the agent finds the exact piece of evidence the decision depends on and asks a human about that one thing. We don't just check the answer. We check whether the decision survives.”

## Recommended pitch reflecting the completed experiment

“Our agent turns an Ezio trust report into an accountable next step: approve, rewrite, pull a source, escalate, or block. It groups sources by origin and shows exactly which evidence each judge saw. A stable vote means the decision holds up across those views; an exposure-driven split is labelled an information gap. The human gets one question about the evidence that matters, and their answer updates the decision. We also show what a simple rule would do. In our real-model EV control, hiding evidence lowered agreement, so we report that limitation openly. This is a traceable decision workflow, not proof that a panel is right.”

## Tools used and reuse disclosure

AI assistants: Claude for backend work, as recorded in the project log, and OpenAI Codex for UI implementation, verification, and demo preparation. TokenRouter supplied the real AI judge experiments using event credits; the deterministic offline judge workflow is separately labelled simulated. Inputs are the four Ezio Try Product sample reports, transcribed from the product screens because no PDF export was available; source notes include transcription and approximate-score limitations. Python, Streamlit, and Plotly power the UI; browser screenshots, Windows speech synthesis, Pillow, and FFmpeg produce the narrated demo walkthrough. We reused our own small statistics utilities written earlier today (balanced evidence partition, n_eff formula).

## Best Use of Ezio (optional)

We use Ezio's claim-level verdicts, source titles and dates, module scores, and findings as individual evidence pieces. Transparent grouping and date checks distinguish listed sources from usable independent origins, and the safety floor prevents silent approval of flagged claims. The EV case also exposes a contradiction between Ezio's verdict and its own quoted figure, giving the accountable human a specific item to verify.

## Research citations from docs/02 §3

- Condorcet (1785), jury theorem: independence is a condition for the classical voting argument, not a claim established for our judges.
- Guneet Kohli (2026), [Nine Judges, Two Effective Votes: Correlated Errors Undermine LLM Evaluation Panels](https://arxiv.org/abs/2605.29800). The reported effective-vote result concerns that study's evaluation datasets, not a measured n_eff for this demo.
- Elliot Kim, Avi Garg, Kenny Peng, and Nikhil Garg (ICML 2025), [Correlated Errors in Large Language Models](https://arxiv.org/abs/2506.07962).
- Tin Kam Ho (1998), [The Random Subspace Method for Constructing Decision Forests](https://doi.org/10.1109/34.709601).
- Leo Breiman (2001), [Random Forests](https://doi.org/10.1023/A:1010933404324).
- Xin Luna Dong, Laure Berti-Équille, and Divesh Srivastava (VLDB 2009), *Integrating Conflicting Data: The Role of Source Dependence*.
- Leslie Kish, effective sample size; project formula: n_eff = n / (1 + (n−1)·mean correlation). The real saved decisions do not supply n_eff, so the UI does not manufacture it.

## Submission assets

- Video: `ui/video/condorcet_streamlit_demo.mp4` — narrated screen-capture walkthrough, EV plus Nuclear, saved human-answer states and real-model control.
- Repository URL: [harshilmehta1512/condorcet-agent](https://github.com/harshilmehta1512/condorcet-agent).
- UI: run `streamlit run ui/app.py --theme.base light`; local verified page at http://127.0.0.1:8502.
- This file is a draft. Nothing has been submitted or published externally.
