"""Run: python -m streamlit run ui/app.py. All displayed evidence comes from saved artifacts."""
import base64
import html
import json
from pathlib import Path
import sys
import uuid

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ui.data import catalog, guide_message, read_json, title
from ui.review import submit_review

COLORS = {
    "APPROVE": ("#24735B", "#E7F3EB"), "REWRITE": ("#A56A17", "#FAF0DB"),
    "PULL_SOURCE": ("#346FA1", "#E8F0F8"), "ESCALATE": ("#7753A1", "#F0EAF6"),
    "BLOCK": ("#A74E48", "#F9ECE9"), "PENDING": ("#6B7B70", "#EDF1EC"),
}
STATUS = {"STABLE": "Stable", "INFO_GAP": "Information gap", "FRAGILE": "Split panel"}
ACTION_TEXT = {
    "APPROVE": "Use the answer as it stands.", "REWRITE": "Revise the flagged wording before use.",
    "PULL_SOURCE": "Find an additional independent source before use.",
    "ESCALATE": "An accountable human needs to review the evidence.", "BLOCK": "Hold this answer from use while the flagged issues are resolved.",
}
ACTION_LABELS = {
    "APPROVE": "Ready to use", "REWRITE": "Edit before use", "PULL_SOURCE": "Find another source",
    "ESCALATE": "Ask a reviewer", "BLOCK": "Hold before use",
}


def esc(value):
    return html.escape(str(value if value is not None else "—"), quote=True)


def markup(value):
    st.markdown(value, unsafe_allow_html=True)


def badge(action):
    color, tint = COLORS.get(action, COLORS["PENDING"])
    return f'<span class="badge" style="--accent:{color};--tint:{tint}">{esc(action.replace("_", " "))}</span>'


def refs(ids):
    return "".join(f'<span class="ref">{esc(eid)}</span>' for eid in ids)


def section(heading, detail=""):
    markup(f'<div class="section-title"><h2>{esc(heading)}</h2><span>{esc(detail)}</span></div>')


def mark_step(name, step):
    progress = st.session_state.setdefault("review_steps", {})
    progress.setdefault(name, set()).add(step)


def buddy(message, complete=False):
    path = Path(__file__).parent / "assets" / "buddy.png"
    image = f'data:image/png;base64,{base64.b64encode(path.read_bytes()).decode()}' if path.exists() else ""
    # JSON encoding plus escaping '<' prevents report text from closing a script tag.
    text = json.dumps(message).replace("<", "\\u003c")
    components.html(f'''<!doctype html><html><head><meta charset="utf-8"><style>
    *{{box-sizing:border-box}}body{{margin:0;font-family:system-ui,sans-serif;color:#35513f}}
    .card{{height:225px;background:#eef3e7;border:1px solid #dbe5d4;border-radius:15px;position:relative;padding:19px 18px;overflow:hidden}}
    .label{{font-size:9px;letter-spacing:1.7px;font-weight:750;color:#7b8c6e}}.title{{font-size:15px;letter-spacing:-.3px;font-weight:650;margin:6px 0 13px}}
    .bubble{{position:relative;z-index:2;max-width:68%;max-height:137px;overflow:auto;font-size:11px;line-height:1.65;background:#ffffffdc;border:1px solid #e0e9d7;border-radius:10px 10px 3px 10px;padding:10px;min-height:85px}}
    img{{position:absolute;right:5px;bottom:14px;height:145px;filter:drop-shadow(0 7px 6px #354b2220);animation:float 4s ease-in-out infinite}}
    .small{{position:absolute;bottom:14px;left:18px;font-size:9px;color:#89947f}}button{{border:0;background:none;color:#597646;font-size:9px;padding:8px 0;cursor:pointer}}
    @keyframes float{{0%,100%{{transform:translateY(0) rotate(-2deg)}}50%{{transform:translateY(-6px) rotate(1deg)}}}}
    @media(prefers-reduced-motion:reduce){{img{{animation:none}}}}
    </style></head><body><div class="card"><div class="label">YOUR EVIDENCE COMPANION</div><div class="title">{'Careful review. Nicely done.' if complete else 'A little help from Buddy.'}</div>
    <div class="bubble"><span id="words" aria-hidden="true"></span><span style="position:absolute;width:1px;height:1px;overflow:hidden">{esc(message)}</span></div>
    <button id="skip" type="button">Show full message ↗</button><img src="{image}" alt="BuddyV, the orange review companion"><div class="small">Text only · grounded in this report</div></div>
    <script>const text={text};const words=document.getElementById('words');let i=0;let timer;
    function all(){{clearTimeout(timer);words.textContent=text;document.getElementById('skip').hidden=true;}}
    function tick(){{words.textContent=text.slice(0,++i);if(i<text.length)timer=setTimeout(tick,13);else document.getElementById('skip').hidden=true;}}
    document.getElementById('skip').onclick=all;if(matchMedia('(prefers-reduced-motion: reduce)').matches)all();else tick();</script></body></html>''', height=230)


def state_card(label, state, tally=None):
    color = COLORS.get(state.get("action"), COLORS["PENDING"])[0]
    markup(f'<div class="state-card" style="--accent:{color}"><div class="card-label">{esc(label)}</div>'
           f'<h3>{esc(state.get("action", "PENDING").replace("_", " "))}</h3>'
           f'<span class="badge status-badge">{esc(STATUS.get(state.get("status"), state.get("status", "Pending")))}</span>'
           f'<p>{esc(tally or state.get("tally", {}))}</p></div>')


def evidence_view(name, decision):
    pieces = decision.get("evidence", [])
    section("Follow the evidence", "Every claim has a trail")
    rows = []
    for piece in pieces:
        origin = (f'<span class="origins">{esc(piece.get("n_sources", 0))} sources → {esc(piece.get("n_origins", 0))} origins</span>'
                  f'<div class="origin-note">{len(piece.get("predating", []))} predating source(s) excluded</div>') if piece.get("kind") == "claim" else "—"
        verdict = piece.get("verdict") or piece.get("severity") or piece.get("kind", "").title()
        rows.append(f'<tr><td>{refs([piece.get("id"), piece.get("ref")])}</td><td class="claim-text">{esc(piece.get("text") or piece.get("summary"))}</td>'
                    f'<td>{esc(verdict)}</td><td>{origin}</td></tr>')
    markup('<div class="table-wrap"><table class="evidence-table"><thead><tr><th>Reference</th><th>Evidence</th><th>Report finding</th><th>Source independence</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')
    st.caption("Origins are heuristic groups within each claim. Publication-date exclusions do not establish that the remaining sources verify a claim.")
    for piece in pieces:
        if piece.get("kind") != "claim":
            continue
        with st.expander(f"{piece.get('ref')} · Source trail · {piece.get('n_sources', 0)} listed → {piece.get('n_origins', 0)} usable origins"):
            st.write(piece.get("text", piece.get("summary", "")))
            early = set(piece.get("predating", []))
            for group in piece.get("origins", []):
                st.caption(" + ".join(group.get("ids", [])) + " · " + (", ".join(group.get("why", [])) or "No shared origin detected by the grouping rules"))
            st.dataframe([{"ID": s.get("id"), "Title": s.get("title"), "Outlet": s.get("outlet"),
                           "Date": s.get("date"), "Type": s.get("type"),
                           "Use": "Excluded: predates period" if s.get("id") in early else "Included in grouping"}
                          for s in piece.get("sources", [])], hide_index=True, width="stretch")
    if st.session_state.get("guided_mode"):
        st.button("I've inspected the source trails", key=f"evidence_{name}", on_click=mark_step, args=(name, "Evidence"))


def panel_view(name, decision):
    panel = decision.get("panel") or {}
    pieces = decision.get("evidence", [])
    votes = panel.get("votes", [])
    section("Judge panel", "What each judge saw and cited")
    simulated = panel.get("mode") != "llm"
    st.caption("Simulated judges (rule-based). Model-family independence has not been measured." if simulated else "LLM judges. Evidence exposure varies; model agreement is not a correctness estimate.")
    header = ''.join(f'<th class="matrix-head" title="{esc(p.get("summary"))}">{esc(p.get("id"))}<br>{esc(p.get("ref"))}</th>' for p in pieces)
    rows = []
    for index, vote in enumerate(votes, 1):
        name_label = f"Judge {index:02d}" if simulated else vote.get("judge")
        model_label = "Simulated · rule-based" if simulated else vote.get("model")
        cells = ''.join(f'<td class="matrix-cell"><span role="img" aria-label="{esc(p.get("id"))}: {"cited" if p.get("id") in vote.get("cited", []) else "seen" if p.get("id") in vote.get("saw", []) else "not shown"}" class="matrix-dot {"cited" if p.get("id") in vote.get("cited", []) else "seen" if p.get("id") in vote.get("saw", []) else ""}" title="{esc(p.get("id"))}: {"cited" if p.get("id") in vote.get("cited", []) else "seen" if p.get("id") in vote.get("saw", []) else "not shown"}"></span></td>' for p in pieces)
        rows.append(f'<tr><td><div class="judge-name">{esc(name_label)}</div><div class="model-name">{esc(model_label)}</div></td>{cells}<td>{badge(vote.get("action", "PENDING"))}</td></tr>')
    markup(f'<div class="table-wrap"><table class="panel-table"><thead><tr><th>Judge</th>{header}<th>Vote</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')
    markup('<div class="legend"><span class="matrix-dot cited"></span> Cited <span class="matrix-dot seen"></span> Shown <span class="matrix-dot"></span> Not shown</div>')
    tally = panel.get("tally") or {}
    total = sum(tally.values())
    if total:
        markup('<div class="tally-track">' + ''.join(f'<div style="width:{count / total * 100}%;background:{COLORS.get(action, COLORS["PENDING"])[0]}"></div>' for action, count in tally.items()) + '</div>')
        markup('<div class="tally-key">' + ''.join(f'<span><i style="background:{COLORS.get(action, COLORS["PENDING"])[0]}"></i>{esc(action.replace("_", " "))} · {count}</span>' for action, count in tally.items()) + '</div>')
    st.caption(f"Top-action share: {panel.get('top_share', 0):.0%} · Status: {decision.get('status')} · Stable threshold: 70%")
    if decision.get("provenance"):
        st.caption("Historical structured votes, validated against saved evidence and citations. Original raw model replies were not supplied.")
    if panel.get("n_eff") is not None:
        st.caption(f"Estimated effective votes: {panel['n_eff']} (see trace for estimation assumptions).")
    flip = decision.get("flip_evidence")
    if flip:
        fixed = {eid for rule in decision.get("hard_rules", []) if rule.get("triggered") for eid in rule.get("evidence", [])}
        is_rule = flip.get("id") in fixed
        caption = "Already flagged by a hard rule" if is_rule else "Evidence associated with the split"
        note = "This is a rule trigger, not additional evidence discovered beyond the rule." if is_rule else "Exposure patterns show association; they do not establish that this piece caused the split."
        markup(f'<div class="callout"><div class="card-label">{caption}</div><b>{esc(flip.get("id"))} · {esc(flip.get("ref"))}</b><br>{esc(note)}<br>'
               f'Shown: {esc(flip.get("saw_it", {}))} · Not shown: {esc(flip.get("didnt", {}))}</div>')
        if flip.get("note"):
            st.caption(flip["note"])
    else:
        st.info("No split evidence is reported for this decision.")
    with st.expander("Read each judge's rationale"):
        for index, vote in enumerate(votes, 1):
            st.write(f"**Judge {index:02d} · {vote.get('action')}** — {vote.get('why', '')}")
            st.caption("Cited: " + ", ".join(vote.get("cited", [])))
    if panel.get("failed"):
        st.warning(f"{len(panel['failed'])} judges were excluded. Inspect the audit artifact for the recorded failures.")
    if st.session_state.get("guided_mode"):
        st.button("I've reviewed the panel", key=f"panel_{name}", on_click=mark_step, args=(name, "Panel"))


def human_view(name, initial, decision, saved_after):
    section("What to do next")
    question = (initial.get("human") or {}).get("question")
    owner = (initial.get("human") or {}).get("to", "Accountable reviewer")
    target = (initial.get("human") or {}).get("ref") or (initial.get("flip_evidence") or {}).get("ref")
    piece = next((p for p in initial.get("evidence", []) if p.get("ref") == target), {})
    if question:
        st.write(f"**{owner}**, please confirm or correct this evidence from a source you trust.")
        markup(f'<div class="review-question">{esc(piece.get("text") or piece.get("summary") or question)} {refs([target] if target else [])}</div>')
    else:
        st.write(ACTION_TEXT.get(decision.get("action"), "Review the evidence before use."))
    after = st.session_state.get("review_results", {}).get(name) or saved_after
    if after and after.get("before"):
        with st.expander("See how a human answer changed the decision"):
            left, right = st.columns(2)
            with left:
                state_card("Before human review", after["before"])
            with right:
                state_card("After human review", after, (after.get("panel") or {}).get("tally"))
            answer = (after.get("human") or {}).get("answer")
            if answer:
                st.write(answer)
            st.caption("A human statement is attributed evidence, not an independent source check. Saved examples are historical.")
    if not question:
        return
    with st.form(f"human_form_{name}"):
        outcome = st.radio("What did you find?", ["Confirmed", "Needs correction", "Still unsure"], index=2, horizontal=True)
        answer = st.text_area("Your answer", placeholder="Name the source you checked and what you found.", height=80)
        submitted = st.form_submit_button("Update decision", type="primary")
        st.caption("Runs a local simulation. Your saved report stays unchanged.")
    if submitted:
        if not answer.strip():
            st.error("Add the source, correction, or uncertainty before submitting.")
        else:
            prefix = {"Confirmed": "Confirmed: ", "Needs correction": "Denied: ", "Still unsure": "Inconclusive: "}[outcome]
            try:
                with st.spinner("Adding your answer to every judge's evidence…"):
                    updated = submit_review(name, initial, prefix + answer, st.session_state["review_session"])
                st.session_state.setdefault("review_results", {})[name] = updated
                st.session_state["versions"][name] = "Your review"
                mark_step(name, "Human review")
                st.rerun()
            except (ValueError, RuntimeError, OSError) as error:
                st.error(str(error))
    if st.session_state.get("guided_mode"):
        st.button("I've reviewed the human handoff", key=f"human_{name}", on_click=mark_step, args=(name, "Human review"))


def audit_view(name, decision, parsed):
    section("A decision you can inspect", "Reasons, guardrails, and limitations")
    for index, reason in enumerate(decision.get("reasons", []), 1):
        markup(f'<div class="reason"><span class="reason-n">{index:02d}</span><div>{esc(reason.get("text"))}<br>{refs(reason.get("evidence", []))}</div></div>')
    section("Hard-rule floor")
    for rule in decision.get("hard_rules", []):
        markup(f'<div class="rule"><b>{"Triggered" if rule.get("triggered") else "Not triggered"}</b> · {esc(rule.get("rule"))}{refs(rule.get("evidence", []))}</div>')
    section("What the report could not check")
    if decision.get("unchecked"):
        for statement in decision["unchecked"]:
            st.write("• " + statement)
    else:
        st.caption("The engine did not identify additional unchecked numeric sentences. That heuristic is not a completeness guarantee.")
    with st.expander("Input provenance & analyzed answer"):
        st.write(parsed.get("source_note", "No source provenance was supplied."))
        st.write(parsed.get("analyzed_text", "No analyzed answer is available."))
    with st.expander("Decision trace"):
        for index, entry in enumerate(decision.get("trace", []), 1):
            st.text(f"{index:02d}  {entry}")
    with st.expander("Raw decision artifact"):
        st.json(decision)
    st.download_button("Download decision JSON", json.dumps(decision, indent=2, ensure_ascii=False), f"{name}.review.json", "application/json")
    if st.session_state.get("guided_mode"):
        st.button("I've read the decision limits", key=f"limits_{name}", on_click=mark_step, args=(name, "Limits"))


def main():
    st.set_page_config(page_title="Condorcet · Evidence workspace", page_icon="◈", layout="wide")
    st.markdown(f'<style>{(Path(__file__).parent / "styles.css").read_text(encoding="utf-8")}</style>', unsafe_allow_html=True)
    st.session_state.setdefault("selected_report", "ev_market")
    st.session_state.setdefault("review_session", str(uuid.uuid4()))
    st.session_state.setdefault("versions", {})
    with st.sidebar:
        markup('<div class="brand"><div class="brand-symbol">c</div><div><div class="brand-name">condorcet</div><div class="brand-sub">Evidence before action</div></div></div>')
        st.caption("CHOOSE A REPORT")
        for name in catalog():
            if st.button(title(name)[0], key=f"pick_{name}", width="stretch",
                         type="primary" if st.session_state["selected_report"] == name else "secondary"):
                st.session_state["selected_report"] = name
                st.rerun()
        name = st.session_state["selected_report"]
        companion = False
        guided = False
        with st.expander("Buddy & review options"):
            companion = st.toggle("Show Buddy", value=False)
            guided = st.toggle("Guided review", value=False, key="guided_mode")
            if companion:
                st.selectbox("Buddy's focus", ["Explain the decision", "Source independence", "What to verify"], key=f"topic_{name}")
            steps = st.session_state.get("review_steps", {}).get(name, set())
            if guided:
                st.progress(len(steps) / 4)
                for step in ["Evidence", "Panel", "Human review", "Limits"]:
                    st.caption(("✓ " if step in steps else "○ ") + step)
                if len(steps) == 4:
                    st.success("Review complete")
                st.caption("Progress records review steps, not correctness.")
        st.caption("Evidence before action.")
    parsed, parsed_error = read_json(ROOT / "parsed" / f"{name}.json")
    initial, decision_error = read_json(ROOT / "decisions" / f"{name}.json")
    after, _ = read_json(ROOT / "decisions" / f"{name}.after_human.json")
    markup(f'<div class="title-line"><h1>{esc(title(name)[0])}</h1></div>')
    if decision_error or parsed_error:
        st.warning(f"This report is not ready yet. {decision_error or parsed_error}")
        st.caption("Choose another report from the library. The workspace stays available when artifacts are missing or invalid.")
        return
    variants = {"Simulated review": initial}
    if after:
        variants["Saved human review"] = after
    for suffix, label in [("llm_subspace", "Real models · evidence slices"), ("llm_full_evidence", "Real models · full evidence")]:
        saved, _ = read_json(ROOT / "decisions" / f"{name}.{suffix}.json")
        if saved:
            variants[label] = saved
    if name in st.session_state.get("review_results", {}):
        variants["Your review"] = st.session_state["review_results"][name]
    versions = list(variants)
    desired = st.session_state["versions"].get(name, versions[0])
    if len(versions) > 1:
        selected = st.selectbox("Review result", versions, index=versions.index(desired) if desired in versions else 0,
                                key=f"version_{name}_{len(versions)}")
    else:
        selected = versions[0]
    st.session_state["versions"][name] = selected
    decision = variants[selected]
    context = decision.get("context") or {}
    markup(f'<div class="question">{esc(parsed.get("question", "Review this answer and its evidence."))}</div>')
    panel = decision.get("panel") or {}
    simulated = panel.get("mode") != "llm"
    st.caption("Simulated judges (rule-based)" if simulated else "Saved LLM votes · revalidated locally · no new model calls")
    tabs = st.tabs(["Decision", "Judge panel", "Evidence trail"])
    with tabs[0]:
        action = decision.get("action", "PENDING")
        color, tint = COLORS.get(action, COLORS["PENDING"])
        left, right = st.columns([2.15, 1], gap="medium") if companion else (st.container(), None)
        with left:
            markup(f'<div class="decision-card" style="--accent:{color};--tint:{tint}"><div class="card-label">Decision</div>'
                   f'<div class="decision-action">{esc(ACTION_LABELS.get(action, "Review needed"))}</div>'
                   f'<div class="decision-copy">{esc(ACTION_TEXT.get(action, "Review the evidence before deciding."))}</div>'
                   f'<div class="decision-footer"><span>Reviewer <b>{esc(context.get("accountable"))}</b></span></div></div>')
        if companion:
            with right:
                buddy(guide_message(decision, st.session_state.get(f"topic_{name}", "Explain the decision")), guided and len(steps) == 4)
        section("Why this decision")
        pieces = decision.get("evidence", [])
        fixed = {eid for rule in decision.get("hard_rules", []) if rule.get("triggered") for eid in rule.get("evidence", [])}
        focus = next((p for p in pieces if p.get("id") in fixed and p.get("kind") == "claim"), None)
        focus = focus or next((p for p in pieces if p.get("ref") == ((decision.get("human") or {}).get("ref") or (decision.get("flip_evidence") or {}).get("ref"))), None)
        focus = focus or next((p for p in pieces if p.get("id") in fixed), None)
        if action == "PULL_SOURCE":
            from ui.data import resolve_source_focus
            focus = resolve_source_focus(decision) or focus
        if focus:
            verdict = str(focus.get("verdict", "")).lower()
            self_conflict = any("matches the claim" in r.get("text", "") and focus.get("ref") in r.get("evidence", []) for r in decision.get("reasons", []))
            if action == "PULL_SOURCE" and focus.get("kind") == "claim":
                explanation = f"This claim lists {focus.get('n_sources', 0)} sources, but they form only {focus.get('n_origins', 0)} usable origin groups. Find another independent source before use."
            elif self_conflict:
                explanation = "The report flags a contradiction, but the figure it quotes matches the claim. The reviewer needs to check this mismatch."
            elif "contradict" in verdict or "false" in verdict:
                explanation = "The report marks this claim as contradicted. It needs checking before the answer can be used."
            elif "not enough" in verdict or "unverif" in verdict:
                explanation = "The report could not verify this claim. More evidence or a human review is needed."
            else:
                explanation = focus.get("summary", "Review the flagged evidence before use.")
            markup(f'<div class="plain-reason">{esc(explanation)} {refs([focus.get("ref")])}</div>')
        else:
            st.write("The reviewers reached the current action across the evidence they were shown. Read the supporting details before use.")
        human_view(name, initial if simulated else decision, decision, after if simulated else None)
        with st.expander("Explore evidence and decision details"):
            baseline = decision.get("baseline") or {}
            adds = decision.get("panel_adds") or {}
            markup(f'<div class="baseline"><strong>Simple rule: {esc(baseline.get("action", "Not recorded").replace("_", " "))}</strong>'
                   f' · Panel differs: {"Yes" if adds.get("value") else "No"} — {esc(adds.get("detail", "Comparison unavailable"))}</div>')
            st.caption(f"Engine action: {action} · Status: {decision.get('status', 'Pending')} · Top vote: {panel.get('top_share', 0):.0%}")
            audit_view(name, decision, parsed)
    with tabs[1]:
        panel_view(name, decision)
    with tabs[2]:
        evidence_view(name, decision)
    markup(f'<details class="provenance"><summary>About this report</summary><p>{esc(parsed.get("source_note", "Source provenance unavailable."))}</p></details>')
    st.caption("Panel agreement does not establish correctness.")


if __name__ == "__main__":
    main()
