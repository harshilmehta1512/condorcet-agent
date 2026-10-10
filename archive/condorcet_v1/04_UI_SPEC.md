# 04 — UI Specification (Streamlit, `app.py`)

**Goal of the UI:** in under 3 minutes, a judge should *see*:
1. 9 AI judges given the same evidence agree with each other, including when they're wrong.
2. That agreement is worth only X independent votes.
3. Giving them different evidence changes that number (whatever the result is).

**Data sources:** only `data/items.jsonl`, `results/results.jsonl`, `results/metrics.json` (rule B3: no hand-typed numbers).
**Default mode:** replay of recorded results. **Optional:** "Run live" for one claim (stretch).
**Build order:** on fake data from `scripts/make_fake_data.py` first; switch to real files at ~2:05 PM by changing one path constant.

---

## Layout: sidebar + 4 tabs, in demo order

### Sidebar
- Title: **Condorcet**, subtitle "What is your AI jury actually worth?"
- Data mode: `Recorded results` (default) / `Fake data (dev)`
- Claim picker (dropdown of item_ids + first 60 characters of each claim) with a **"Show a false-consensus example"** button that jumps to an item where panel A was confidently wrong
- Footer: N items, n judges, r, seed, source citations

### Tab 1 — "The question"
Purpose: set up the story in 20 seconds.
- Claim shown large.
- Abstract sentences as a numbered list; **human-marked evidence sentences highlighted** (green border) with a badge "Human label: SUPPORT / CONTRADICT".
- Analogy box (expander): *"If all your weather apps use the same forecast model, checking 9 apps is like checking 1."*

### Tab 2 — "Standard panel (A): everyone sees everything"
Purpose: show agreement that looks like certainty.
- **3×3 grid of judge cards** (one per model): model name, verdict chip (green = correct, red = wrong, grey = abstain), "saw 100% of evidence".
- **Panel verdict banner:** e.g. "9 / 9 agree: SUPPORT ✗ (human label: CONTRADICT)", red when wrong.
- Call-out under a false-consensus example: *"Unanimous and wrong. Nine votes, one mistake, repeated."*

### Tab 3 — "Split-evidence panel (B): each judge sees a different slice"
Purpose: make the method visible.
- **Evidence-assignment matrix** (Plotly heatmap): rows = 9 judges, columns = sentences; filled cell = judge saw the sentence; gold sentences outlined. A caption explains that each sentence is seen by r judges and each judge sees about 40%.
- Same 3×3 judge cards, plus an "informed / uninformed" tag; NOT_ENOUGH_INFO shown in grey ("correctly abstained" when uninformed).
- Panel B verdict banner, the same style as Tab 2, placed **side by side** with panel A's verdict for this claim.

### Tab 4 — "Results: what is the jury worth?" (the main screen)
Top row, 4 KPI tiles (A vs B each), with CIs in small text:
1. **Effective judges (n_eff)**, e.g. "9 judges → 2.1 effective" vs "9 → X". This is the biggest number on the page.
2. **Panel accuracy** vs **best single judge** (same items). Shows "Panel beats best judge? Yes/No".
3. **Condorcet gap**: predicted-if-independent vs observed.
4. **False consensus rate**: confident majority, wrong.

Charts:
- **A. Error-correlation heatmaps** (9×9), A and B side by side, same colour scale (0 → 1). Darker for A tells the story at a glance.
- **B. "More judges isn't more truth" curve:** x = number of judges (1…9), y = n_eff; three lines: ideal independent (y = x), panel A, panel B. Computed from ρ̄ with Kish's formula for each n.
- **C. Agreement → probability table** (A and B): "When 9/9 agree → right 91% [83–95]". This answers "should we act on this verdict?"
- **D. Hypothesis scorecard:** H1–H4 with ✅ / ❌ / inconclusive and a one-line detail, read from `metrics.json`. A failed H3/H4 is shown as-is, never hidden.

Bottom: **"Trust calculator"**: two dropdowns, "k of n judges agreed" and "panel type A/B" → "Measured probability this verdict is right: X% [CI]". This turns the research into a tool a team would use.

---

## Visual rules
- Colours: correct = green, wrong = red, abstain/escalate = grey, panel A = orange, panel B = blue. Use the same colours everywhere.
- Every chart caption states N and that labels are from human annotators.
- Every number has its CI in smaller text beneath it.
- No animations that could break the demo. Use Plotly static configs.
- Fits a 1440×900 projector without scrolling in Tab 4's top section.

## Demo script against the UI (3 minutes)
| Time | Screen | Say |
|---|---|---|
| 0:00 | Tab 1 | "Many teams here built a panel of AI judges. The idea: if many models agree, trust it." |
| 0:20 | Tab 2 (false-consensus example) | "Nine judges, unanimous, and wrong. Research shows nine LLM judges are worth about two votes. Here's our measurement on scientific claims." |
| 0:50 | Tab 4, KPI 1 + heatmap A | "Our panel: 9 judges, X effective. The best single judge does as well as the whole panel." |
| 1:30 | Tab 3 | "Random forests solved this 25 years ago: give each tree different features. We gave each judge different evidence." |
| 2:00 | Tab 4, A vs B + scorecard | Report H3/H4 exactly as measured. |
| 2:30 | Trust calculator | "Instead of '9 agreed', you get the measured probability it's right. That's decision-grade." |
| 2:50 | — | "Agreement isn't trust. Independence is." |

## Fake data generator (`scripts/make_fake_data.py`, Person 2, first 15 min)
- 30 fake items with 8–12 sentences each, 1–2 gold indices, random gold labels.
- Fake results: panel A judges share a hidden "difficulty" variable so errors correlate (ρ ≈ 0.4); panel B weaker correlation, more abstentions.
- Fake `metrics.json`: **produced by running the real `analysis.py` on the fake results** once Person 1 has it. Until then, a hand-written placeholder JSON with every Contract 3 key, clearly marked `"FAKE": true`. The UI shows a red "FAKE DATA" banner whenever `meta.FAKE` is true.
