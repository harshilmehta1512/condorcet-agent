# Streamlit walkthrough

`condorcet_streamlit_demo.mp4` is the new 1:56 narrated walkthrough of actual browser screenshots. It shows EV, the saved human-answer update, Nuclear for over 20 seconds, and the saved real TokenRouter experiment/control. Simulated judges, saved states, and synthetic speech are disclosed in the video. Captions are in `condorcet_streamlit_demo.srt`; the scene timing is in `timeline.json`.

The original `condorcet_demo.mp4` and `condorcet_live_demo.mp4` from the repository are preserved.

To regenerate the new walkthrough on Windows, from the repository root:

```powershell
python -m pip install -r ui/requirements-video.txt
& .\ui\video\synthesize_narration.ps1
python ui/video/build_video.py
```

The script uses local Windows SAPI speech synthesis and the nine captured JPEGs. It makes no LLM calls. Generated WAVs and intermediate video segments are ignored by Git.
