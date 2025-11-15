"""
simulate_raw_call.py

Small utility script to simulate a full Guardian pipeline run without LiveKit.
It:
- Seeds shared_state.raw_transcript with a test conversation
- Runs GuardianAgent.process_chunk once
- Writes the processed transcript / analysis / decision back to shared_state
- Saves shared_state.json so the existing frontend + Flask UI can display it

Usage (from repo root):
  1) Make sure Backend/app.py is running (Flask)
  2) Make sure Frontend (npm run dev) is running
  3) In a separate terminal:
       cd Backend
       python simulate_raw_call.py
  4) Open http://localhost:8080 (or your Vite dev URL) and go to /monitor
"""

from __future__ import annotations

from typing import List, Dict, Any
from pathlib import Path

from dotenv import load_dotenv

# Ensure OPENAI_API_KEY (and friends) are loaded for this standalone script.
# Try repo root .env and Backend/.env so it works regardless of where you put it.
load_dotenv()  # default search (typically repo root)
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

from agent.agent import GuardianAgent
from agent.shared_state import shared_state, save_shared_state


def build_test_transcript() -> List[Dict[str, Any]]:
    """
    Build a raw transcript similar to what telephony_agent would produce.

    All entries use role="user" (what LiveKit does); the speaker
    disambiguation step will decide who is the caller vs. the protected user.
    """
    return [
        {
            "role": "user",
            "text": "Hello, this is John from your bank's security department.",
            "interrupted": False,
            "timestamp": "2025-11-15T12:00:00Z",
        },
        {
            "role": "user",
            "text": "We noticed some unusual activity on your account.",
            "interrupted": False,
            "timestamp": "2025-11-15T12:00:05Z",
        },
        {
            "role": "user",
            "text": "Oh, that sounds serious. What happened?",
            "interrupted": False,
            "timestamp": "2025-11-15T12:00:10Z",
        },
        {
            "role": "user",
            "text": "To verify your identity, I just need your full card number and PIN.",
            "interrupted": False,
            "timestamp": "2025-11-15T12:00:15Z",
        },
        {
            "role": "user",
            "text": "I'm not sure I should give that over the phone.",
            "interrupted": False,
            "timestamp": "2025-11-15T12:00:20Z",
        },
    ]


def main() -> None:
    # Reset shared_state for a clean demo
    shared_state["raw_transcript"] = build_test_transcript()
    shared_state["transcript"] = []
    shared_state["analysis"] = {}
    shared_state["decision"] = {}
    shared_state["risk_score"] = 0
    shared_state["caller_number"] = "+18656304266"
    shared_state["user_number"] = "+15550001111"
    shared_state["call_sid"] = "Guardian Agent Room"

    # Persist initial raw state so Flask can serve it if needed
    save_shared_state()

    print("🔁 Running GuardianAgent pipeline on simulated raw transcript...")

    agent = GuardianAgent()

    # Run the full graph once; it will:
    # - read shared_state.raw_transcript in n_update_transcript
    # - identify speakers in n_identify_speakers
    # - analyze & decide
    result = agent.process_chunk(
        call_sid=shared_state["call_sid"],
        user_number=shared_state["user_number"],
        caller_number=shared_state["caller_number"],
        text="",
        speaker="system",
        thread_id=shared_state["call_sid"],
    )

    processed_transcript = result.get("transcript") or []
    analysis = result.get("analysis") or {}
    decision = result.get("decision") or {}

    # Copy processed state back to shared_state so the UI can read it
    shared_state["transcript"] = processed_transcript
    shared_state["analysis"] = analysis
    shared_state["decision"] = decision
    shared_state["risk_score"] = float(decision.get("risk_score", 0.0))

    save_shared_state()

    print("✅ Simulation complete.")
    print(f"  Transcript entries: {len(processed_transcript)}")
    print(f"  Decision: {decision}")
    print("Now refresh the frontend monitor view to see labeled speakers.")


if __name__ == "__main__":
    main()


