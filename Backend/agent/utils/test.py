import os
import json

# If you use a .env file, uncomment:
from dotenv import load_dotenv

load_dotenv()

# 👇 adjust this import to wherever you put the function
# e.g. from agent.utils.check_speaker import identify_speakers
from check_speaker import identify_speakers


def pretty_print_transcript(title, transcript):
    print(f"\n===== {title} =====")
    for i, entry in enumerate(transcript):
        speaker = entry.get("speaker", "unknown")
        text = entry.get("text", "")
        print(f"{i:02d} [{speaker}]: {text}")
    print("=" * 30 + "\n")


def main():
    # Make sure your API key is set
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set in environment")

    # Example transcript:
    # - agent: your AI guardian
    # - user: currently used for BOTH real user and scammer (what we want to fix)

    transcript = [
        {"speaker": "agent", "text": "I’ll monitor quietly."},
        # scammer barrage (3 in a row)
        {"speaker": "user", "text": "Ma’am, this is the bank security line."},
        {
            "speaker": "user",
            "text": "We detected $3,200 sent overseas from your account.",
        },
        {
            "speaker": "user",
            "text": "You must stay on this recorded line until we verify your identity.",
        },
        # actual elderly user
        {"speaker": "user", "text": "What? I didn’t send anything… what’s going on?"},
        # scammer again
        {
            "speaker": "user",
            "text": "Please remain calm. I will guide you step by step.",
        },
    ]
    pretty_print_transcript("ORIGINAL TRANSCRIPT", transcript)

    # Call your classifier
    updated = identify_speakers(transcript)

    pretty_print_transcript("UPDATED TRANSCRIPT (WITH SPEAKER IDENTIFICATION)", updated)

    # Optional: dump to JSON so you can inspect easily
    print("Raw updated JSON:\n")
    print(json.dumps(updated, indent=2))


if __name__ == "__main__":
    main()
