"""Read report artifacts without assuming every file or optional field exists."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLES = {
    "ev_market": ("EV market", "Mobility & markets", "EV"),
    "nuclear": ("Nuclear energy", "Energy & policy", "NE"),
    "work_from_home": ("Work from home", "Work & society", "WF"),
    "agi_timelines": ("AGI timelines", "Technology & strategy", "AI"),
}
CONTEXTS = {
    "ev_market": "analyst_client_note",
    "nuclear": "policy_brief",
    "work_from_home": "comms_publish",
    "agi_timelines": "strategy_memo",
}


def read_json(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return (data, None) if isinstance(data, dict) else (None, "Expected a JSON object.")
    except FileNotFoundError:
        return None, "File is not available yet."
    except (OSError, ValueError) as error:
        return None, f"Could not read this artifact ({type(error).__name__})."


def catalog(root=ROOT):
    names = set(TITLES)
    names.update(p.stem for p in (root / "parsed").glob("*.json") if not p.stem.startswith("_"))
    return sorted(names, key=lambda name: list(TITLES).index(name) if name in TITLES else 99)


def title(name):
    return TITLES.get(name, (name.replace("_", " ").title(), "Trust report", name[:2].upper()))


def resolve_source_focus(decision):
    claims = [p for p in decision.get("evidence", []) if p.get("kind") == "claim"]
    return max(claims, key=lambda p: (p.get("n_sources", 0) - p.get("n_origins", 0), p.get("n_sources", 0)), default=None)


def guide_message(decision, topic):
    action = decision.get("action", "PENDING").replace("_", " ").lower()
    if topic == "Source independence":
        piece = resolve_source_focus(decision)
        if piece:
            return (f"Look at {piece['ref']}: {piece.get('n_sources', 0)} listed sources become "
                    f"{piece.get('n_origins', 0)} usable origins. Open its source trail to see the grouping "
                    "and dates. These are heuristic groups, not proof of independence.")
        return "Open the evidence trail and check where each claim's sources came from. Repeated sources can share an origin."
    if topic == "What to verify":
        human = decision.get("human") or {}
        if human.get("question"):
            return f"{human.get('to', 'The accountable reviewer')} has the next step: {human['question']}"
        return "Check the source trail and unresolved report limitations before using this answer. A stable panel is not proof of correctness."
    status = decision.get("status", "PENDING")
    if status == "INFO_GAP":
        focus = (decision.get("flip_evidence") or {}).get("ref", "the flagged claim")
        return (f"The current action is {action}. Votes differ by evidence exposure. Check {focus} and the safety rules. "
                "The split alone does not prove uncertainty.")
    if status == "STABLE":
        return f"The current action is {action}. The panel's top vote holds up across the sampled evidence views. Agreement does not establish correctness."
    return f"The current action is {action}. The panel is split across evidence views. Start with the evidence, then bring unresolved questions to the accountable reviewer."
