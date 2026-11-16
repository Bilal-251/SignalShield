import os
from pathlib import Path

# Key without a terminal: put a file named .env next to this file containing:  COHERE_API_KEY=your_key
_env = Path(__file__).with_name(".env")
if _env.exists():
    for _l in _env.read_text().splitlines():
        if "=" in _l and not _l.strip().startswith("#"):
            _k, _v = _l.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

MODEL = os.environ.get("SS_MODEL", "command-a-03-2025")

# USD per token. Command A list price: $2.50 in / $10 out per 1M (check your dashboard).
PRICE_IN = 2.50e-6
PRICE_CACHED = 2.50e-6
PRICE_OUT = 10.00e-6

# Hard stop. The wrapper refuses new API calls once recorded spend reaches this.
BUDGET_USD = float(os.environ.get("SS_BUDGET", "400"))

TEMPERATURE = 0.3
THINK_BUDGET = None  # Command A has no thinking mode. (Command A+ needs a number like 800 here.)  # Command A+ must think: turning it off makes it write its reasoning into the answer text
MAX_COMPLETION = 2500  # includes thinking tokens
MAX_STEPS = 4  # model calls with tools before the forced final answer

ARMS_CORE = ["A0", "A1", "A3", "A4", "A6", "A7"]
ARMS_EXTRA = ["A2", "A5"]

ARMS = {
    "A0": dict(inband=None, oob=False, forge=None, reverse=False),
    "A1": dict(inband="tier", oob=False, forge=None, reverse=False),
    "A2": dict(inband="track", oob=False, forge=None, reverse=False),
    "A3": dict(inband=None, oob=True, forge=None, reverse=False),
    "A4": dict(inband="tier", oob=False, forge="tier", reverse=False),
    "A5": dict(inband="track", oob=False, forge="track", reverse=False),
    "A6": dict(inband=None, oob=True, forge="tier", reverse=False),
    "A7": dict(inband="tier", oob=False, forge=None, reverse=True),
}

TIER_DOMAINS = {
    "High": ["national-records-office.example", "institute-of-statistics.example", "academy-press-archive.example"],
    "Med": ["regional-gazette.example", "city-chronicle.example", "trade-journal-weekly.example"],
    "Low": ["dailyscoop-blog.example", "forum-digest-hub.example", "viral-facts-now.example"],
}