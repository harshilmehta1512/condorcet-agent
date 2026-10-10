"""Build ui/condorcet.html from decisions/*.json (no server, no dependencies). Run: python ui/build_html.py"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "decisions"
COL = {"APPROVE": "#1f9d55", "REWRITE": "#d97706", "PULL_SOURCE": "#2563eb", "ESCALATE": "#7c3aed", "BLOCK": "#dc2626"}
REPORTS = [("ev_market", "EV market"), ("agi_timelines", "AGI timelines"), ("work_from_home", "Work from home"), ("nuclear", "Nuclear")]
e = html.escape


def load(name):
    p = D / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def badge(a):
    return f'<span class="b" style="background:{COL.get(a, "#555")}">{e(a)}</span>'


def card(d, title=""):
    c, p = d["context"], d["panel"]
    ev = [x for x in d["evidence"] if x["kind"] != "human"]
    rows = "".join(
        f'<tr><td>{e(x["id"])}</td><td>{e(x.get("ref",""))}</td><td>{e(x.get("verdict", x["kind"]))}</td>'
        f'<td>{(str(x["n_sources"]) + " → " + str(x["n_origins"]) + " usable origins" + (f" ({len(x[chr(112)+"redating"])} too early)" if x.get("predating") else "")) if x["kind"]=="claim" else ""}</td></tr>'
        for x in ev)
    ids = [x["id"] for x in ev]
    grid = "".join(
        f'<tr><td>{e(v["judge"])}</td>' + "".join(f'<td class="{"on" if i in v["saw"] else ""}"></td>' for i in ids)
        + f'<td>{badge(v["action"])}</td><td class="why">{e(v["why"][:110])}</td></tr>' for v in p["votes"])
    reasons = "".join(f"<li>{e(r['text'])}</li>" for r in d["reasons"])
    b = d.get("baseline") or {}
    adds = d.get("panel_adds") or {}
    hq = d["human"]
    human = (f'<div class="h"><b>To {e(hq["to"])}:</b> {e(hq["question"] or "")}'
             + (f'<br><b>Answer:</b> {e(hq["answer"])}' if hq.get("answer") else "") + "</div>") if hq.get("question") else ""
    before = (f'<div class="ba">Before: {badge(d["before"]["action"])} {e(d["before"]["status"])} → After: {badge(d["action"])} {e(d["status"])}</div>'
              if d.get("before") else "")
    mode = "Saved real-model votes (locally revalidated)" if p["mode"] == "llm" else "simulated judges"
    return f"""<div class="card"><h3>{e(title)}</h3>
<div class="ctx">{e(c["role"])} → {e(c["use"])} · stakes {e(c["stakes"])} · accountable: {e(c["accountable"])} · <i>{mode}, {p.get("condition","subspace")}</i></div>
<div class="dec">{badge(d["action"])} <span class="st">{e(d["status"])}</span> {e(d["headline"])}</div>
<div class="base">Simple rule: {badge(b.get("action","?"))} focus {e(str(b.get("focus")))} · <b>Panel differs from the rule: {"YES" if adds.get("value") else "no"}</b> ({e(adds.get("detail",""))})</div>
{before}{human}
<h4>Evidence (source entries → usable origin groups)</h4><table>{rows}</table>
<h4>Judge panel: who saw what</h4><table class="g"><tr><th>judge</th>{"".join(f"<th>{i}</th>" for i in ids)}<th>action</th><th>why</th></tr>{grid}</table>
<div class="t">Tally {e(json.dumps(p["tally"]))} · answered {p["n_judges"]}{" · failed " + str(p.get("n_failed")) if p.get("n_failed") else ""}</div>
<h4>Reasons</h4><ol>{reasons}</ol></div>"""


parts = []
ev_full, ev_sub = load("ev_market.llm_full_evidence"), load("ev_market.llm_subspace")
if ev_full and ev_sub:
    parts.append(f"""<div class="card exp"><h2>Saved real-model experiment (EV, corrected validation)</h2>
<p><b>Full evidence:</b> {e(json.dumps(ev_full["panel"]["tally"]))} → {badge(ev_full["action"])} {e(ev_full["status"])} &nbsp; | &nbsp;
<b>Split evidence:</b> {e(json.dumps(ev_sub["panel"]["tally"]))} → {e(ev_sub["status"])}</p>
<p>Both validated panels are STABLE/REWRITE. The five models common to both panels give identical votes (4 REWRITE, 1 PULL_SOURCE). Answering rosters differ; aggregate shares do not establish a benefit or causal effect from hiding evidence. Original raw replies were not supplied; validation uses saved structured votes.</p></div>""")
for name, title in REPORTS:
    d = load(name)
    if d:
        parts.append(card(d, f"{title}: initial decision"))
    a = load(f"{name}.after_human")
    if a:
        parts.append(card(a, f"{title}: after the human answers"))
if ev_full:
    parts.append(card(ev_full, "EV market: real AI judges, full evidence"))
if ev_sub:
    parts.append(card(ev_sub, "EV market: real AI judges, split evidence"))

page = f"""<!doctype html><html><head><meta charset="utf-8"><title>Condorcet Agent</title><style>
body{{font-family:-apple-system,Segoe UI,sans-serif;margin:24px;background:#0f1117;color:#e7e9ee}}
h1{{margin:0}} .sub{{color:#9aa3b2;margin-bottom:18px}}
.card{{background:#171a23;border:1px solid #2a2f3d;border-radius:10px;padding:16px;margin:16px 0}}
.exp{{border-color:#7c3aed}} .b{{color:#fff;padding:3px 9px;border-radius:6px;font-weight:700;font-size:13px}}
.st{{border:1px solid #9aa3b2;border-radius:6px;padding:2px 7px;margin:0 6px;font-size:12px}}
.dec{{font-size:17px;margin:10px 0}} .ctx,.t{{color:#9aa3b2;font-size:13px}} .base{{margin:8px 0;font-size:14px}}
.ba{{background:#1e2230;padding:8px;border-radius:8px;margin:8px 0}} .h{{background:#22192f;padding:8px;border-radius:8px;margin:8px 0}}
table{{border-collapse:collapse;font-size:13px;margin:6px 0}} td,th{{border:1px solid #2a2f3d;padding:4px 7px;text-align:left}}
.g td.on{{background:#3b82f6}} .why{{color:#b8bfcc;max-width:520px}} h4{{margin:12px 0 4px}}
</style></head><body><h1>Condorcet Agent</h1>
<div class="sub">A trust agent for Ezio reports: counts independent evidence, checks the verifier, and asks a human about the evidence a decision depends on. Inputs are Ezio sample reports transcribed from screenshots (no export available).</div>
{''.join(parts)}</body></html>"""
(ROOT / "ui").mkdir(exist_ok=True)
(ROOT / "ui" / "condorcet.html").write_text(page, encoding="utf-8")
print("wrote", ROOT / "ui" / "condorcet.html")
