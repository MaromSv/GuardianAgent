# app.py
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from agent.agent import GuardianAgent
from agent.shared_state import get_shared_state

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Enable CORS for all routes (allows frontend to access backend)
CORS(app)

# Create ONE shared agent instance
# (MemorySaver inside it stores per-call state by call_sid)
agent = GuardianAgent()


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "GuardianAgent backend running"})


# Endpoint for Twilio or your STT service to send transcript chunks
@app.route("/calls/<call_sid>/transcript", methods=["POST"])
def handle_transcript(call_sid):
    """
    Expected JSON body:
    {
        "text": "caller audio transcription",
        "speaker": "caller" | "user",
        "user_number": "+1555..",
        "caller_number": "+1555.."
    }
    """
    data = request.get_json(force=True)

    text = data.get("text", "")
    speaker = data.get("speaker", "caller")
    user_number = data.get("user_number", "")
    caller_number = data.get("caller_number", "")

    # Process chunk with the LangGraph agent
    state = agent.process_chunk(
        call_sid=call_sid,
        user_number=user_number,
        caller_number=caller_number,
        text=text,
        speaker=speaker,
        thread_id=call_sid,  # ensures state persists per-call
    )

    # What we return is up to you for debugging / testing
    return jsonify(
        {
            "decision": state.get("decision"),
            "analysis": state.get("analysis"),
            "audio_url": state.get("guardian_utterance_audio_url"),
            "activity": state.get("activity"),
        }
    )


# Endpoint to get the currently active call
@app.route("/calls/active", methods=["GET"])
def get_active_call():
    """
    Returns the active call SID.
    
    Note: This is a simplified version that just returns the known LiveKit room name.
    In production, you'd want to use a persistent checkpoint store (SQLite, Redis, etc.)
    so both Flask and telephony_agent can share state.
    
    For now, we just return the hardcoded room name and let the frontend try to fetch it.
    """
    # LiveKit always uses "Guardian Agent Room" as the room name
    # The frontend will try to fetch /calls/Guardian%20Agent%20Room/state
    # If there's no data, it'll just show empty/loading
    call_sid = "Guardian Agent Room"
    
    return jsonify({
        "call_sid": call_sid,
        "status": "active",
        "user_number": None,
        "caller_number": None,
    })


# Endpoint to fetch the current state of a call
@app.route("/calls/state", methods=["GET"])
def get_call_state():
    """
    Return the entire agent state from shared_state.
    For demo purposes, we just return the global shared_state.
    """
    # Get the shared state (this is shared between Flask and telephony_agent in the same process)
    state_dict = get_shared_state()
    
    print(f"[DEBUG] GET /calls/state - shared_state contains: {list(state_dict.keys())}")
    print(f"[DEBUG] Transcript length: {len(state_dict.get('transcript', []))}")
    
    # Return in the format the frontend expects: {"state": {"values": {...}}}
    return jsonify(
        {
            "state": {
                "values": state_dict
            }
        }
    )


if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    
    # Run Flask development server
    print(f"Starting GuardianAgent Flask server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
