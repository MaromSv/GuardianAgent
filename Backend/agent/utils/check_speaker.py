from typing import List, Dict, Any
import os
import json
from openai import OpenAI

_client = None


def _get_openai_client():
    """Lazy-load OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")

        base_url = os.getenv("OPENAI_BASE_URL")
        if base_url:
            _client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            _client = OpenAI(api_key=api_key)
    return _client


def identify_speakers(
    transcript: List[Dict[str, str]],
    user_number: str = None,
    caller_number: str = None,
) -> List[Dict[str, str]]:
    """
    Re-label messages to distinguish between:
      - 'user'               (elderly protected person)
      - 'pottential_scammer' (other human on the line/caller)
      - 'agent'              (AI assistant)

    Handles both raw format (with "role" field) and processed format (with "speaker" field).
    No heuristics: only the LLM decides speaker identification.
    """
    if not transcript:
        return transcript

    # First pass: Normalize "role" → "speaker" and "assistant" → "agent"
    normalized_transcript = []
    for entry in transcript:
        # Get speaker from either "speaker" or "role" field
        speaker = entry.get("speaker") or entry.get("role", "unknown")

        # Map assistant → agent
        if speaker == "assistant":
            speaker = "agent"

        normalized_transcript.append(
            {
                "speaker": speaker,
                "text": entry.get("text", ""),
                "interrupted": entry.get("interrupted", False),
                "timestamp": entry.get("timestamp", ""),
            }
        )

    # Find entries that need speaker identification (currently labeled as "user")
    # These are human messages that could be from either the elderly person OR the scammer
    needs_identification = [
        i
        for i, entry in enumerate(normalized_transcript)
        if entry.get("speaker") == "user"
    ]

    if not needs_identification:
        return normalized_transcript

    try:
        labels = _identify_speakers_with_llm(
            transcript=normalized_transcript,
            indices_to_identify=needs_identification,
            user_number=user_number,
            caller_number=caller_number,
        )

        updated = normalized_transcript.copy()
        allowed = {"user", "pottential_scammer"}

        for idx, label in zip(needs_identification, labels):
            if isinstance(label, str) and label.lower() in allowed:
                updated[idx] = {
                    **updated[idx],
                    "speaker": label.lower(),
                }
            # If label is something else, we leave it as 'user'

        return updated

    except Exception as e:
        # If the LLM fails, we don't try to be clever - just return normalized transcript
        print(f"Error identifying speakers with LLM: {e}")
        return normalized_transcript


def _identify_speakers_with_llm(
    transcript: List[Dict[str, str]],
    indices_to_identify: List[int],
    user_number: str = None,
    caller_number: str = None,
) -> List[str]:
    """
    LLM-only speaker identification.

    For each entry whose index is in indices_to_identify:
      -> return 'user' or 'pottential_scammer'.
    """
    client = _get_openai_client()

    # Use last 10 messages as context
    context_window = transcript[-10:] if len(transcript) > 10 else transcript
    conversation_text = "\n".join(
        f"[{i}] {entry.get('speaker','unknown').upper()}: {entry.get('text','')}"
        for i, entry in enumerate(context_window)
    )

    system_prompt = """You are analyzing a phone conversation with three logical roles:

- "agent": an AI assistant that may ask questions or warn about scams.
- "user": the elderly person being protected.
- "pottential_scammer": the other human caller, who may be trying to scam the user.

Important:
- In the transcript you see, ALL human messages are currently labeled as "user".
  Your job is to re-label each of those human messages as either:
    - "user"               (the elderly protected person), or
    - "pottential_scammer" (the other human).
- Messages labeled "agent" are from the AI assistant and should NOT be changed.

Clues:
- The pottential_scammer often:
  - leads the conversation,
  - makes claims (e.g. from a company/bank),
  - creates urgency,
  - requests information, codes, or money.
- The user (elderly person) usually:
  - answers questions,
  - expresses uncertainty or confusion,
  - asks for clarification,
  - reacts to what the other person says.

Output:
Return ONLY a JSON object with a single field "labels", which is an array
of strings. Each string MUST be exactly "user" or "pottential_scammer".

Example:
{
  "labels": ["pottential_scammer", "user", "user"]
}
"""

    entries_text = "\n".join(
        f"Entry {idx}: \"{transcript[idx].get('text','')}\""
        for idx in indices_to_identify
    )

    user_prompt = f"""Full conversation context:
{conversation_text}

Entries needing identification:
{entries_text}

Return JSON:
{{ "labels": ["user", "pottential_scammer", ...] }}
The number of labels MUST equal the number of entries listed above,
and they MUST be in the same order.
"""

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=200,
    )

    result = json.loads(response.choices[0].message.content.strip())
    labels = result.get("labels", [])

    if not isinstance(labels, list):
        raise ValueError("LLM returned invalid label structure")

    return labels


def needs_speaker_identification(transcript: List[Dict[str, str]]) -> bool:
    """
    Check if transcript has any entries needing speaker identification.

    Returns True if there are "user" entries (from LiveKit role field) that need
    to be distinguished as either "user" (protected person) or "pottential_scammer".
    """
    for entry in transcript:
        # Check both "speaker" and "role" fields
        speaker = entry.get("speaker") or entry.get("role")
        if speaker == "user":
            return True
    return False
