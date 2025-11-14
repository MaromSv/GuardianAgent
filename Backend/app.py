# app.py
from flask import Flask, request, jsonify
from guardian_agent import GuardianAgent

app = Flask(__name__)

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
    # Re-run with an empty chunk to pull the saved state
    state = agent.graph.get_state(thread_id=call_sid)

    return jsonify(
        {
            "state": state,
        }
    )


if __name__ == "__main__":
    # Run Flask development server
    # Use: python app.py
    print("Starting GuardianAgent Flask server on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
