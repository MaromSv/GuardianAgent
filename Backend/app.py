# app.py
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from agent.agent import GuardianAgent

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


# Endpoint to fetch the current state of a call
@app.route("/calls/<call_sid>/state", methods=["GET"])
def get_call_state(call_sid):
    """
    Return the entire agent state for debugging.
    """
    # Get the saved state using the config format
    checkpoint = agent.graph.get_state(
        config={
            "configurable": {
                "thread_id": call_sid,
            }
        }
    )
    
    # Extract values from checkpoint (checkpoint is a tuple/list, values are at index 0)
    # Or use checkpoint.values if it's a Checkpoint object
    if checkpoint is None:
        return jsonify({"state": {"values": None}})
    
    # Handle tuple/list checkpoint structure
    if isinstance(checkpoint, (list, tuple)) and len(checkpoint) > 0:
        values = checkpoint[0]
    elif hasattr(checkpoint, 'values'):
        values = checkpoint.values
    else:
        values = checkpoint

    return jsonify(
        {
            "state": {
                "values": values,
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
