"""Read-only decision viewer. Run: streamlit run ui/app.py."""
from __future__ import annotations

import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

# Optional project-local dependencies; normal pip/venv installations work too.
ROOT = Path(__file__).resolve().parents[1]
if (ROOT / ".ui_deps").exists():
    sys.path.insert(0, str(ROOT / ".ui_deps"))
import streamlit as st
import plotly.graph_objects as go

UI = Path(__file__).resolve().parent
COLORS = {"APPROVE": "#087f5b", "REWRITE": "#a86300", "PULL_SOURCE": "#1764ad",
          "ESCALATE": "#7542ba", "BLOCK": "#bc2639", "STABLE": "#087f5b",
          "FRAGILE": "#bc2639", "INFO_GAP": "#a86300", "TRIGGERED": "#bc2639"}


def obj(value):
    return value if isinstance(value, dict) else {}


def rows(value):
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def items(value):
    return value if isinstance(value, list) else []


def esc(value):
    return html.escape(str(value if value is not None else "—"))


def read_json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return (value, None) if isinstance(value, dict) else ({}, "Expected a JSON object")
    except (OSError, ValueError) as error:
        return {}, str(error)


def badge(value):
    return f'<span class="badge" style="background:{COLORS.get(str(value), "#586579")}">{esc(value)}</span>'


def heading(title, anchor):
    st.markdown(f'<h2 id="{anchor}">{esc(title)}</h2>', unsafe_allow_html=True)


def tally_text(value):
    return " · ".join(f"{count} {action}" for action, count in obj(value).items()) or "Waiting for votes"


def policy_threshold(decision):
    # The contract has no threshold field. Display it only when supplied in a reason.
    for reason in rows(decision.get("reasons")):
        match = re.search(r"(\d+(?:\.\d+)?%)\s+(?:needed|required)", str(reason.get("text", "")))
        if match:
            return match.group(1)
    return None


def render_card(decision):
    st.markdown(f'<div class="decision-card">{badge(decision.get("action", "WAITING"))} '
                f'{badge(decision.get("status", "WAITING"))}<p>{esc(decision.get("headline", "Waiting for backend results"))}</p></div>',
                unsafe_allow_html=True)
    baseline, adds = obj(decision.get("baseline")), obj(decision.get("panel_adds"))
    if baseline:
        value = adds.get("value")
        st.markdown(f'<div class="baseline">Simple rule says: <b>{esc(baseline.get("action"))}</b> '
                    f'· focus {esc(baseline.get("focus"))} · Panel adds: <b>{"yes" if value is True else "no" if value is False else "not supplied"}</b>'
                    f'<br>{esc(adds.get("detail", baseline.get("rule")))}</div>', unsafe_allow_html=True)
    else:
        st.caption("Simple-rule baseline not supplied by backend.")


def claim_details(piece, parsed):
    ref = piece.get("ref")
    claim = next((c for c in rows(parsed.get("claims")) if c.get("id") == ref), {})
    st.write(piece.get("text") or claim.get("text") or piece.get("summary") or "Waiting for claim text")
    sources = rows(piece.get("sources")) or rows(claim.get("sources"))
    by_id = {s.get("id"): s for s in sources}
    origins = rows(piece.get("origins"))
    if origins:
        for group in origins:
            st.markdown("**Origin: " + ", ".join(str(x) for x in items(group.get("ids"))) + "**")
            reasons = items(group.get("why"))
            st.caption("Why grouped: " + ("; ".join(map(str, reasons)) if reasons else "No grouping reason supplied; source stands separately."))
            for source_id in items(group.get("ids")):
                source = by_id.get(source_id, {})
                st.write(f'{source_id} · {source.get("title", "Source details unavailable")} · {source.get("outlet") or source.get("type", "")} · {source.get("date") or "date unavailable"}')
    elif sources:
        st.caption("Grouping details were not supplied. Counts above are from the decision JSON.")
        st.dataframe(sources, hide_index=True, width="stretch")
    else:
        st.caption("Waiting for source details")
    predating = items(piece.get("predating"))
    if predating:
        st.warning("Excluded as predating the claim period: " + ", ".join(map(str, predating)))


def render_evidence(decision, parsed):
    heading("Evidence pieces", "evidence")
    evidence = rows(decision.get("evidence"))
    claims = {c.get("id"): c for c in rows(parsed.get("claims"))}
    table = []
    for piece in evidence:
        claim = claims.get(piece.get("ref"), {})
        counts = "—"
        if piece.get("kind") == "claim":
            ns, no = piece.get("n_sources"), piece.get("n_origins")
            counts = f"{ns} sources → {no} independent origin(s)" if ns is not None and no is not None else "Waiting for origin counts"
        table.append({"ID": piece.get("id"), "Kind": piece.get("kind"),
                      "Evidence": piece.get("text") or piece.get("summary"),
                      "Ezio verdict": piece.get("verdict") or claim.get("verdict") or "—",
                      "Source independence": counts})
    if table:
        st.dataframe(table, hide_index=True, width="stretch", height="content")
    else:
        st.info("Waiting for backend results: evidence pieces")
    for piece in evidence:
        if piece.get("kind") == "claim":
            with st.expander(f'{piece.get("id", "?")} · {piece.get("ref", "Claim")} — sources and grouping'):
                claim_details(piece, parsed)


def render_panel(decision):
    heading("Different judges. Different evidence views.", "panel")
    panel = obj(decision.get("panel"))
    evidence = rows(decision.get("evidence"))
    votes = rows(panel.get("votes"))
    if not votes:
        st.info("Waiting for backend results: judge panel")
        return
    mode = panel.get("mode")
    st.caption(f'{panel.get("n_judges", len(votes))} answering judges · {"SIMULATED JUDGES · deterministic offline rules" if mode == "offline-mock" else "Real AI judges · TokenRouter" if mode == "llm" else "Judge mode not supplied"} · {panel.get("condition", "evidence slices")}')
    st.caption("Filled cell = evidence seen · outlined cell = evidence hidden · action labels = individual votes, before the final safety floor")
    ids = [p.get("id") for p in evidence if p.get("id")]
    grid = '<div class="grid-wrap"><table class="judge-grid"><thead><tr><th>Judge / model</th>'
    grid += "".join(f'<th title="{esc(p.get("summary"))}">{esc(p.get("id"))}</th>' for p in evidence if p.get("id"))
    grid += '<th>Vote</th></tr></thead><tbody>'
    for vote in votes:
        grid += f'<tr><td class="model">{esc(vote.get("judge"))}<small>{esc(vote.get("model"))}</small></td>'
        seen = items(vote.get("saw"))
        for eid in ids:
            visible = eid in seen
            grid += f'<td title="{esc(eid)}: {"seen" if visible else "hidden"}"><span class="cell {"seen" if visible else "hidden"}">{"●" if visible else "○"}</span></td>'
        grid += f'<td>{badge(vote.get("action", "WAITING"))}</td></tr>'
    grid += '</tbody></table></div>'
    st.markdown(grid, unsafe_allow_html=True)
    tally = {a: n for a, n in obj(panel.get("tally")).items() if isinstance(n, (int, float)) and not isinstance(n, bool) and n >= 0}
    if tally:
        fig = go.Figure()
        for action, count in tally.items():
            fig.add_trace(go.Bar(y=["Votes"], x=[count], name=str(action), orientation="h",
                                marker_color=COLORS.get(action, "#586579"), text=[f"{action} · {count}"],
                                textposition="inside", insidetextanchor="middle", hovertemplate=f"{esc(action)}: %{{x}}<extra></extra>"))
        fig.update_layout(barmode="stack", height=110, margin=dict(l=0, r=0, t=5, b=5),
                          showlegend=False, xaxis=dict(visible=False), yaxis=dict(visible=False),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=16, color="white"))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    share = panel.get("top_share")
    if isinstance(share, (int, float)) and not isinstance(share, bool):
        threshold = policy_threshold(decision)
        line = f'Top action share {share:.0%} → {decision.get("status", "WAITING")}'
        line += f" · STABLE needs ≥ {threshold}" if threshold else " · Stability threshold not supplied in JSON"
        st.markdown(f'<div class="share">{esc(line)}</div>', unsafe_allow_html=True)
    if panel.get("n_eff") is not None:
        st.caption(f'n_eff ≈ {panel["n_eff"]} of {panel.get("n_judges", len(votes))} · supplied backend estimate')
    else:
        st.caption("n_eff not supplied; no independence estimate inferred from this single panel.")
    failed = rows(panel.get("failed"))
    if failed:
        st.warning(f'{panel.get("n_failed", len(failed))} judges failed and were excluded from the tally.')
        with st.expander("Failed judges"):
            st.dataframe(failed, hide_index=True, width="stretch")
    with st.expander("Judge explanations and cited evidence"):
        for vote in votes:
            st.write(f'{vote.get("judge")} · {vote.get("action")} · cited: {", ".join(map(str, items(vote.get("cited"))))}')
            st.caption(vote.get("why") or "Explanation not supplied")


def render_flip(decision, parsed):
    flip = obj(decision.get("flip_evidence"))
    if not flip or decision.get("status") not in ("FRAGILE", "INFO_GAP"):
        return
    heading("Evidence the decision depends on", "flip")
    piece = next((p for p in rows(decision.get("evidence")) if p.get("id") == flip.get("id")), {})
    st.warning(f'Decision depends on {flip.get("id", "?")} ({piece.get("kind", "evidence")} {flip.get("ref") or piece.get("ref", "")}). '
               f'Judges who saw it → {tally_text(flip.get("saw_it"))}; judges who did not → {tally_text(flip.get("didnt"))}.')
    if decision.get("status") == "INFO_GAP":
        st.info("This split is explained by evidence exposure: an information gap created by hiding evidence. It is not reported as genuine uncertainty.")
    claim_details(piece, parsed)


def render_reasons(decision):
    heading("Reasons and the safety floor", "reasons")
    for index, reason in enumerate(rows(decision.get("reasons")), start=1):
        st.write(f'{index}. {reason.get("text", "Waiting for reason")}')
        st.caption("Evidence: " + ", ".join(map(str, items(reason.get("evidence")))))
    for rule in rows(decision.get("hard_rules")):
        triggered = rule.get("triggered") is True
        label = "TRIGGERED" if triggered else "✓ Not triggered" if rule.get("triggered") is False else "Waiting for rule result"
        st.markdown(f'<div class="rule">{badge(label) if triggered else esc(label)} · {esc(rule.get("rule"))}</div>', unsafe_allow_html=True)
    with st.expander("What the report couldn't check"):
        unchecked = items(decision.get("unchecked"))
        for text in unchecked:
            st.write(f"☐ {text}")
        if not unchecked:
            st.caption("No unchecked statements supplied. This does not establish completeness.")


def render_comparison(after):
    before = obj(after.get("before"))
    if not before:
        st.info("Waiting for backend results: previous decision")
        return
    for col, title, data in zip(st.columns(2), ["BEFORE", "AFTER"], [before, after]):
        with col:
            st.markdown(f'<div class="comparison"><b>{title}</b><p>{badge(data.get("action", "WAITING"))} {badge(data.get("status", "WAITING"))}</p>{esc(tally_text(data.get("tally") if title == "BEFORE" else obj(data.get("panel")).get("tally")))}</div>', unsafe_allow_html=True)


def context_path(context):
    for path in sorted((ROOT / "contexts").glob("*.json")):
        value, error = read_json(path)
        if not error and all(value.get(k) == context.get(k) for k in ("role", "use", "stakes", "accountable")):
            return path
    return None


def run_human(decision, source_path, parsed_path, answer, offline):
    """Backend process writes only UI-owned files. Seed its previous state for before→after."""
    context = context_path(obj(decision.get("context")))
    if not context or not parsed_path.exists():
        return None, "Waiting for backend results: matching report/context file is missing."
    name = str(decision.get("report", ""))
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        return None, "Invalid report identifier."
    output = UI / "live_results" / "decisions"
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, output / f"{name}.json")
    env = os.environ.copy()
    env["CONDORCET_OUT"] = str(output)
    env["CONDORCET_CACHE"] = str(UI / "live_results" / "cache")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    command = [sys.executable, "-m", "agent.run", "--report", str(parsed_path), "--context", str(context), "--human", answer]
    if offline:
        command.append("--offline")
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=180,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, f"Agent command failed: {error}"
    if result.returncode:
        return None, (result.stderr or result.stdout or "Agent returned an error")[-6000:]
    value, error = read_json(output / f"{name}.json")
    return value, error


def main():
    st.set_page_config(page_title="Condorcet Agent", page_icon="◈", layout="wide")
    st.markdown('''<style>
    .stApp{background:#f5f7fb;color:#162638}.block-container{max-width:1160px;padding-top:1.4rem;padding-bottom:3rem}
    h1{font-size:2.25rem!important;letter-spacing:-.06em}h2{font-size:1.4rem!important;margin-top:1.6rem!important}
    .badge{display:inline-block;border-radius:6px;padding:6px 12px;color:white;font-size:14px;font-weight:750;white-space:nowrap}
    .decision-card{background:white;border:1px solid #dce3ed;border-left:5px solid #293e59;border-radius:10px;padding:20px;margin-top:14px}
    .decision-card>.badge{font-size:21px;padding:8px 16px}.decision-card p{font-size:18px;margin:14px 0 0}
    .baseline{background:#eaf0f6;border-radius:7px;padding:12px 16px;margin-top:8px;font-size:14px}
    .grid-wrap{overflow-x:auto;background:white;border:1px solid #dce3ed;border-radius:10px}
    .judge-grid{width:100%;border-collapse:collapse;font-size:14px}.judge-grid th{background:#eaf0f6;color:#293e59;text-align:center;padding:9px}
    .judge-grid td{padding:4px 8px;line-height:1.2;border-top:1px solid #eaf0f6;text-align:center}.judge-grid td.model{text-align:left;min-width:210px;max-width:300px;font-weight:650}
    .judge-grid .badge{font-size:12px;padding:6px 8px}
    .model small{display:block;font-weight:400;font-size:11px;color:#586579;overflow-wrap:anywhere}
    .cell{display:inline-block;border-radius:5px;width:27px;line-height:27px}.seen{background:#224d72;color:white}.hidden{background:#f0f3f7;color:#8c9aab}
    .share{font-size:18px;font-weight:650}.rule{padding:8px 0}.comparison{background:white;border:1px solid #dce3ed;border-radius:10px;padding:20px}
    </style>''', unsafe_allow_html=True)
    st.title("◈ Condorcet Agent")
    st.caption("Does the decision hold up across different evidence views?")
    paths = sorted(p for p in (ROOT / "decisions").glob("*.json") if not p.name.startswith("_") and ".after_human." not in p.name)
    sample = not paths
    if sample:
        paths = [UI / "sample_decision.json", UI / "sample_decision_stable.json"]
    names = {path.name: path for path in paths}
    requested = st.query_params.get("report", "ev_market.json")
    default = list(names).index(requested) if requested in names else 0
    chosen = st.selectbox("Report / saved result", list(names), index=default,
                          format_func=lambda n: n.removesuffix(".json").replace("_", " ").replace(".llm", " · real AI"))
    source_path = names[chosen]
    decision, error = read_json(source_path)
    if sample:
        st.error("SAMPLE DATA — synthetic fixture; not an Ezio report or real judge run.")
    if error:
        st.info("Waiting for backend results: " + error)
        st.button("Reload results", on_click=st.rerun)
        return
    name = str(decision.get("report", ""))
    safe_name = name if re.fullmatch(r"[A-Za-z0-9_-]+", name) else "missing"
    parsed_path = UI / ("sample_parsed_stable.json" if "stable" in chosen else "sample_parsed.json") if sample else ROOT / "parsed" / f"{safe_name}.json"
    parsed, parsed_error = read_json(parsed_path)
    context = obj(decision.get("context"))
    st.write(f'{context.get("role", "Waiting for role")} → {context.get("use", "Waiting for use")} · {context.get("stakes", "unknown")} stakes · accountable: {context.get("accountable", "not supplied")}')
    st.markdown(f'**Original question:** {parsed.get("question") or decision.get("question") or "Waiting for backend results"}')
    if parsed.get("source_note"):
        st.caption("Input provenance: " + str(parsed["source_note"]))
    if parsed_error:
        st.info("Waiting for backend results: parsed report. Available decision data is shown below.")
    mode = obj(decision.get("panel")).get("mode")
    if mode == "offline-mock":
        st.warning("SIMULATED JUDGES — deterministic offline rules; the evidence is from the Ezio report.")
    elif mode == "llm":
        st.info("REAL AI JUDGES — saved TokenRouter experiment. Failed judges are excluded.")
        st.caption("On this EV experiment, hiding evidence lowered agreement; it did not reveal hidden disagreement. Panel adds is the backend's action/focus comparison, not a measured improvement.")
    elif not sample:
        st.warning("Judge mode not supplied by backend; do not assume these are real AI votes.")
    render_card(decision)
    render_evidence(decision, parsed)
    render_panel(decision)
    render_flip(decision, parsed)
    render_reasons(decision)
    heading("Human in the loop", "human")
    human = obj(decision.get("human"))
    st.write(f'To: {human.get("to") or context.get("accountable", "not supplied")} — {human.get("question") or "No human question supplied for this decision."}')
    if human.get("answer"):
        st.write("Recorded answer: " + str(human["answer"]))
    saved_path = ROOT / "decisions" / f"{safe_name}.after_human.json"
    saved, saved_error = read_json(saved_path)
    if not sample and not saved_error:
        st.caption("Saved demo state · simulated judges · recorded human answer; no live call")
        show_saved = st.checkbox("Show saved BEFORE → AFTER", value=st.query_params.get("after") == "saved", key=f"saved-{chosen}")
        if show_saved:
            st.write("Recorded answer: " + str(obj(saved.get("human")).get("answer", "not supplied")))
            render_comparison(saved)
    if decision.get("before"):
        render_comparison(decision)
    with st.form(f"human-{chosen}"):
        answer = st.text_area("Accountable person's answer", placeholder="Confirm, correct, or explain the flagged evidence.")
        offline = st.checkbox("Use deterministic offline judges (demo-safe)", value=True)
        submitted = st.form_submit_button("Submit answer and rerun", disabled=sample or not human.get("question"))
    if submitted:
        if not answer.strip():
            st.error("Enter an answer before submitting.")
        else:
            with st.spinner("Running the agent and reloading the result…"):
                result, run_error = run_human(decision, source_path, parsed_path, answer.strip(), offline)
            if run_error:
                st.error("Agent command failed. " + run_error)
            else:
                st.session_state[f"result-{chosen}"] = result
                st.success("Decision reloaded from UI-owned live results.")
    result = st.session_state.get(f"result-{chosen}")
    if result:
        st.caption("Live rerun · " + str(obj(result.get("panel")).get("mode", "mode not supplied")))
        render_comparison(result)
        with st.expander("Updated evidence, reasons and trace"):
            st.json(result)
    with st.expander("Trace"):
        for step in items(decision.get("trace")):
            st.write(str(step))
        st.caption(f"Decision file: {source_path.relative_to(ROOT)}")
    st.button("Reload results", on_click=st.rerun)


if __name__ == "__main__":
    main()
