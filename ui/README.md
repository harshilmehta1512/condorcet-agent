# UI and demo handoff

Run from the repository root:

```powershell
streamlit run ui/app.py --theme.base light
```

The verified local instance is http://127.0.0.1:8502. If using the project-local dependency folder in this workspace:

```powershell
$env:PYTHONPATH = Join-Path $PWD '.ui_deps'
python -m streamlit run ui/app.py --global.developmentMode false --server.port 8502 --server.headless true --theme.base light
```

The picker lists real decision files, excludes synthetic backend tests and after-human snapshots, and falls back to the two UI fixtures when no real decision files exist. Saved after-human results appear in the human-review section and are labelled simulated. The live command receives the selected parsed report and matching context as separate arguments; output and cache are isolated under `ui/live_results`, preserving teammate-owned files. Offline mode is enabled by default. Live failures appear as UI errors.

The locked example has no stability-threshold key or source-grouping metadata. The UI extracts the threshold only from backend reason text, reads grouping details when present in real files, and marks missing fields as unavailable. Real decisions currently omit n_eff; the UI does not infer it.

`video/condorcet_streamlit_demo.mp4` is a narrated walkthrough of actual browser screenshots at 1280×720, with saved human-answer states. It is not a continuous live screen recording. Windows speech synthesis provides the voice; the frame header discloses this. EV and Nuclear are both shown, with simulated-judge labels retained, followed by the real TokenRouter subspace/control results and their limitation. `video/condorcet_streamlit_demo.srt` and `video/timeline.json` accompany the video.

Submission text is in `submission_draft.md`. Repository: https://github.com/harshilmehta1512/condorcet-agent. The team must submit the assets; no buildathon submission has been performed.

The `.ui_deps` directory is a local runtime installation, not a submission asset. Exclude it, `ui/live_results`, intermediate WAV/segment files, and Python caches from a repository upload. Keep the final MP4, subtitles, scene manifest, source, fixtures, and submission draft.
