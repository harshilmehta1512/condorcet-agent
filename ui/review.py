"""Isolate local human-review runs from the repository's saved demo decisions."""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from ui.data import CONTEXTS, ROOT, read_json


def submit_review(name, decision, answer, session_id, root=ROOT):
    if name not in CONTEXTS:
        raise ValueError("A decision context must be configured for this report.")
    session_id = str(uuid.UUID(session_id))
    target = (decision.get("human") or {}).get("ref") or (decision.get("flip_evidence") or {}).get("ref")
    if not target:
        raise ValueError("This decision has no evidence target for a human answer.")
    if not answer.strip():
        raise ValueError("Write a confirmation, correction, or unresolved question first.")
    out = root / "cache" / "ui-reviews" / session_id
    out.mkdir(parents=True, exist_ok=True)
    artifact = out / f"{name}.json"
    artifact.write_text(json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8")
    env = dict(os.environ, CONDORCET_OUT=str(out), PYTHONUTF8="1")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "agent.run", "--report", str(root / "parsed" / f"{name}.json"),
             "--context", str(root / "contexts" / f"{CONTEXTS[name]}.json"), "--offline",
             "--human", answer.strip(), "--human-ref", target],
            cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=45,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("The review timed out. Your original demo files are unchanged.") from None
    if result.returncode:
        raise RuntimeError("The review could not be completed. The saved report is unchanged.")
    updated, error = read_json(artifact)
    if error:
        raise RuntimeError(error)
    return updated
