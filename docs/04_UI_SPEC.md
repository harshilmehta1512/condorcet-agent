# 04 — UI and Demo Video Spec (teammate; LOCKED 1:46 PM)

**Required deliverable:** a 1–2 minute video: the agent takes in the main report, decides, explains; then a second report (≥ 20 s) with a different, sensible decision.
**Stack:** Streamlit, `ui/app.py`. Reads only `parsed/*.json` and `decisions/*.json` (contracts in `03` §2). Until real files exist, build on `ui/sample_decision.json` with a visible "SAMPLE DATA" banner.

## Layout (top to bottom = video order)

1. **Header:** report picker (4 reports), decision context ("Analyst → client note · high stakes · accountable: Research lead"), and the original question.
2. **Decision card:** big action badge with text + colour (APPROVE green, REWRITE amber, PULL_SOURCE blue, ESCALATE purple, BLOCK red) and status chip **STABLE** / **FRAGILE**. One-line headline.
3. **Evidence pieces:** a table, one row per piece: id, kind (claim / scores / finding), short text, Ezio verdict, and for claims **"4 sources → 1 independent origin"** (expand to see the grouped sources and why they were grouped).
4. **The judge panel (hero visual):** a grid, rows = 9 judges (model names), columns = evidence pieces. Filled cell = the judge saw it. Last column = the judge's action (coloured badge). It shows at a glance that different judges saw different evidence.
   Below it: vote tally bar + "top action share 56% → FRAGILE (needs ≥ 70%)" + "n_eff ≈ 2.3 of 9".
5. **Flip evidence:** a callout, e.g. "The decision depends on **E3 (claim C3)**: judges who saw it → 4 ESCALATE / 0 APPROVE; judges who didn't → 1 ESCALATE / 4 APPROVE." Plus the claim text and its sources.
6. **Reasons:** numbered, each with evidence id tags. Hard-rule floor: list each rule with ✓ / triggered. "What the report couldn't check."
7. **Human in the loop:** "To: Research lead — <question>". Text box + Submit → runs the agent with `--human` → shows **before → after** side by side (action, status, tally).
8. **Trace** (collapsible).

## Visual rules
- Every status shows text plus colour.
- Readable at 1280×720 (video resolution).
- No hand-typed numbers; everything comes from the JSON.

## Video script (≈ 1:45)
| Time | Show | Say |
|---|---|---|
| 0:00 | Header | "An analyst wants to put this AI answer on the EV market into a client note. Ezio checked it. Should it go out?" |
| 0:12 | Evidence pieces | "Our agent breaks the report into evidence and groups sources by origin." (Mention repeated sources only if real.) |
| 0:25 | Judge panel grid | "Then, like a random forest, nine AI judges each see a different slice of the evidence. Research shows nine judges seeing the same thing are worth about two votes." |
| 0:45 | Tally + flip evidence | "The decision splits. Everyone who saw claim 3 says escalate. So the decision depends on claim 3." |
| 1:00 | Human loop | "It asks the research lead one question about claim 3. She answers, and the decision updates." Before → after. |
| 1:20 | Switch report | "Same agent, work-from-home report for a comms lead: the panel agrees across all evidence slices, stable, so it acts." |
| 1:40 | Decision card | "We don't just check the answer. We check whether the decision survives." |

Record 2:35–2:55. Two takes max.
