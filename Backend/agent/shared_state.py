from __future__ import annotations

"""
shared_state.py

Very simple shared state between the telephony agent and Flask backend.
For the demo, we also persist this to disk as JSON so that separate
processes (telephony_agent.py and app.py) can see the same data.
"""

from pathlib import Path
import json
from typing import Dict, Any


# Location on disk where we persist the shared state
_STATE_FILE = Path(__file__).resolve().parent / "shared_state.json"


# In‑memory shared state for the telephony agent process
shared_state: Dict[str, Any] = {
    # Raw transcript from LiveKit / telephony_agent (role-based)
    "raw_transcript": [],
    # Processed transcript from GuardianAgent (speaker-disambiguated)
    "transcript": [],
    "analysis": {},
    "decision": {},
    "risk_score": 0,
    "caller_number": None,
    "user_number": None,
    "call_sid": None,
}


def _load_from_disk() -> None:
    """Load shared_state from disk into memory (best‑effort)."""
    if not _STATE_FILE.exists():
        return
    try:
        with _STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            shared_state.update(data)
    except Exception as e:
        print(f"[shared_state] Warning: could not load state from disk: {e}")


def save_shared_state() -> None:
    """Persist the current shared_state to disk as JSON."""
    try:
        with _STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(shared_state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[shared_state] Warning: could not save state to disk: {e}")


def get_shared_state() -> Dict[str, Any]:
    """
    Return the latest shared_state.
    For Flask (separate process), this will reload from disk first.
    """
    _load_from_disk()
    return shared_state