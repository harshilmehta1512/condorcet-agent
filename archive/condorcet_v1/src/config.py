"""Single source of truth for run settings. Edit JUDGES once TokenRouter IDs are confirmed (task T0)."""
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Load KEY=VALUE lines from .env (gitignored) without overriding real environment variables.
_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"'))
RAW_DIR = ROOT / "data" / "raw" / "data"
ITEMS_PATH = ROOT / "data" / "items.jsonl"
ASSIGNMENTS_PATH = ROOT / "data" / "assignments.jsonl"
RESULTS_PATH = ROOT / "results" / "results.jsonl"
METRICS_PATH = ROOT / "results" / "metrics.json"
CACHE_DIR = ROOT / "cache"

SEED = 42
N_ITEMS = int(os.environ.get("CONDORCET_N_ITEMS", 150))
N_PILOT = 20
SUBSET_FRACTION = 0.4

# Judge roster: short name -> model ID on TokenRouter. At most 2 per family (rule C4).
# Candidate IDs; confirm the exact strings on TokenRouter and update here (log it in 05_PROJECT_LOG.md).
JUDGES = {
    "gpt-nano": "gpt-5.4-nano",
    "gpt-mini": "gpt-5.4-mini",
    "haiku": "claude-haiku-5-5",
    "sonnet": "claude-sonnet-5-5",
    "gemini-flash": "gemini-flash-latest",
    "llama": "llama-latest",
    "qwen": "qwen-latest",
    "mistral": "mistral-small-latest",
    "deepseek": "deepseek-chat",
}
N_JUDGES = len(JUDGES)
R = math.ceil(SUBSET_FRACTION * N_JUDGES)  # judges per sentence in condition B

# API: event credits only (rule A1). Deliberately does NOT read OPENAI_API_KEY.
API_BASE_URL = os.environ.get("TOKENROUTER_BASE_URL", "")
API_KEY = os.environ.get("TOKENROUTER_API_KEY", "")
# "mock" = offline simulated judges for pipeline testing (no network, no cost).
PROVIDER = os.environ.get("CONDORCET_PROVIDER", "mock")
CONCURRENCY = 16
TIMEOUT_S = 60
MAX_TOKENS = 50

VERDICTS = ("SUPPORT", "CONTRADICT", "NOT_ENOUGH_INFO")
