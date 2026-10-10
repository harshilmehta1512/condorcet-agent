# Corrected submission and narrated demo

This is the consolidated version to use. It keeps the simple tested UI and adds the newer package's provider-qualified model roster, full-evidence condition, and archived historical real-model votes. Prior downloads are preserved.

## Fixes completed before recording

- A human statement cannot remove a contradicted/critical hard-rule floor. Unresolved answers do not confirm evidence; human target and H1 are explicit and traceable.
- Judge replies must contain a valid action, a nonempty rationale, and valid citations to shown evidence. Failed, malformed, and uncited replies are excluded.
- Flip candidates exclude every piece that triggered a hard rule; uncited candidates and zero-distance associations are not invented as flips. Hard-rule warnings and the human's question target remain separate.
- Exposure-associated disagreement is described as association, not proof of cause or identical full evidence. The UI exposes a simple-rule comparison without implying better accuracy.
- Missing live configuration produces an error instead of silently substituting simulated judges. All nine provider-qualified model IDs were confirmed in a successful free catalog check. API responses are not copied into errors. Request starts are spaced to respect the configured provider rate limit.
- Calendar-date differences use real dates, including month and year boundaries. Active I/O uses UTF-8 on Windows. Unsupported PDF ingestion is stated explicitly; all supplied report inputs are the disclosed screenshot transcriptions.
- The UI has visible Decision, Judge panel, and Evidence trail tabs. Details and Buddy remain optional. The four simulated reports, saved human states, and corrected real-model variants are selectable and tested. Local human submissions cannot overwrite saved decisions.

## Corrected results

| Case | Action | Status | Notes |
| --- | --- | --- | --- |
| EV, simulated initial | ESCALATE | FRAGILE | C1 is separately flagged by a hard rule; C2 is the beyond-rule exposure-associated piece. |
| EV, saved human confirmation | ESCALATE | STABLE | Other claims remain unverified; the safety floor remains in force. |
| Nuclear, simulated | PULL_SOURCE | STABLE | 7 source requests and 2 rewrites. C5 has 6 entries grouped into 3 usable origins. |
| Work from home, simulated | ESCALATE | STABLE | 9 escalation votes. |
| AGI, simulated initial | ESCALATE | INFO_GAP | C1 remains a rule warning; the remaining exposure association is with module scores. |
| AGI, saved human denial | BLOCK | STABLE | H1 is shown to every judge. |
| EV, historical real subspace votes, revalidated | REWRITE | STABLE | 4 REWRITE + 1 PULL_SOURCE; 80% among 5 valid votes. |
| EV, historical full-evidence votes, revalidated | REWRITE | STABLE | 6 REWRITE + 1 PULL_SOURCE; 85.7% among 7 valid votes. |

The two real runs originally included one malformed, uncited answer each. Validation excludes those answers. Among the **five models appearing in both valid panels**, the votes are identical: 4 REWRITE and 1 PULL_SOURCE. The different aggregate shares therefore do not demonstrate a benefit from hiding evidence. This project does not claim improved accuracy, causal independence, or measured effective votes.

Revalidation uses the supplied structured vote records, because the original raw response cache was not present in the download. Original decisions are preserved under `reports/experiments/`, and regenerated artifacts include the source SHA-256 and the validation limitation. No new inference prompts were sent. The model catalog check is the only provider network request in this correction pass.

## Video and validation

- `ui/video/condorcet_demo_corrected.mp4`: narrated walkthrough of eight actual browser screenshots, 1280×720, H.264 video and AAC audio. It is not a continuous live recording. Synthetic voice, saved results, and screenshots are disclosed on every frame.
- `ui/video/condorcet_demo_corrected.srt`: spoken captions; `narration.txt` and `timeline.json` contain the script and exact scene timing.
- Nuclear receives at least 20 seconds. The total duration is within the 1–2 minute brief.
- 26 checks pass, including four-report repeatability, evidence reference integrity, safety-floor enforcement, unresolved answers, valid H1 targets, explicit live configuration, real-vote replay, flip exclusions, calendar boundaries, all UI report/real-model variants, and isolated human submission.

## Reproduce

```powershell
.\.venv\Scripts\python.exe scripts/regenerate_submission.py
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe ui/video/prepare_scenes.py
& .\ui\video\synthesize_narration.ps1
.\.venv\Scripts\python.exe ui/video/build_video.py
```

Install `ui/requirements-video.txt` for video encoding. SAPI speech generation uses Windows' installed synthetic voice. Captured screenshots are included; intermediate WAVs and encoded segments live under ignored `cache/video/`.

## Submission disclosure

Condorcet turns Ezio's claim verdicts, scores, findings, and sources into a traced action, grouped source origins, and a targeted human handoff. It compares panel actions with a simple rule and openly reports that its historical real-model control does not establish an improvement from evidence subspaces.

Claude was used for earlier backend work, and Codex for review, corrections, UI, verification, and video preparation. The morning's small balanced-partition and n_eff statistics utilities were reused as already recorded. Buddy artwork is reused unchanged from the user's MockingIt project and is optional. Windows SAPI provides synthetic narration; Pillow and FFmpeg assemble the screenshot walkthrough. Inputs are screenshot transcriptions with approximate scores disclosed. The default demo and human reruns use simulated rules; historical TokenRouter votes are separately labeled.

The corrected source and video are included in this GitHub repository. The app runs locally; no hosted deployment or buildathon submission has been performed by this chat.
