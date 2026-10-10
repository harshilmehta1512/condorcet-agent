# Corrected UI and demo handoff

Run `start-ui.cmd` on Windows, or `python -m streamlit run ui/app.py` from the repository root after installing requirements. The configured local app is http://127.0.0.1:8501.

Choose a report from the sidebar. The visible tabs are Decision, Judge panel, and Evidence trail. The Decision tab explains the next action and human handoff; detailed rules, reasons, and audit are expandable. Buddy and guided review are optional and off by default. For EV, the Review result selector exposes simulated results, saved human updates, and locally revalidated historical real-model results.

Human submissions use an isolated local simulation under ignored `cache/ui-reviews/`; saved decisions remain intact. Historical LLM votes include validation provenance and the missing-raw-response-cache limitation. No n_eff estimate is invented.

**Use `video/condorcet_demo_corrected.mp4` with `video/condorcet_demo_corrected.srt`.** It is a 1:48 narrated walkthrough of actual browser screenshots, not a continuous live recording. Every frame discloses saved results and synthetic voice. It includes EV, the human answer, Nuclear for 25 seconds, and the corrected real-model comparison.

The older `condorcet_demo.mp4`, `condorcet_live_demo.mp4`, and `condorcet_streamlit_demo.mp4`, plus their capture assets, are preserved from the remote repository as historical versions. Their old experimental conclusions are superseded; do not use them for the corrected submission.

Current submission text is in `submission_draft.md` and `docs/07_SUBMISSION_READY.md`. `build_html.py` produces a static, read-only view from current corrected results; it is not the primary Streamlit UI.
