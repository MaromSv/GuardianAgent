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

    system_prompt = """You are analyzing a phone conversation to identify who is speaking.

There are three roles:
- "agent": AI assistant (already correctly labeled, don't change these)
- "user": the ELDERLY person being PROTECTED (receives the call, answers the phone)
- "pottential_scammer": the CALLER who initiated the call (may be trying to scam the user)

CRITICAL CONTEXT:
- This is an INCOMING call TO the elderly person
- The elderly person ("user") ANSWERS the phone
- The other person ("pottential_scammer") is the one who CALLED

Your job:
Re-label ALL messages currently marked as "user" to be EITHER:
  - "user" (the elderly person who answered the phone)
  - "pottential_scammer" (the person who called them)

How to identify who is who:

THE ELDERLY PERSON ("user"):
- ANSWERS the phone first: "Hello?", "Who is this?", "Yes?"
- Responds to what the caller says
- Asks clarifying questions: "What do you mean?", "Are you okay?"
- Shows concern or confusion: "That sounds terrible", "This seems suspicious"
- Is being CALLED (didn't initiate the conversation)
- May address the caller by name if they know them: "Oh Daniel!"

THE CALLER ("pottential_scammer"):
- CALLED the elderly person (initiated the conversation)
- Introduces themselves: "Hi Uncle Tom, it's me Daniel"
- Explains why they're calling: "I'm in trouble", "I need help"
- Makes requests: "Can you help me?", "I need money", "Can you send..."
- Creates urgency: "I need it TODAY", "I'm desperate"
- Often references family/authority: "I'm your nephew", "The bank said..."

IMPORTANT PATTERNS:
1. First message is USUALLY the elderly person answering: "Hello?" = "user"
2. Second message introduces themselves: "Hi, it's Daniel" = "pottential_scammer"
3. Someone saying "Uncle Tom" or similar IS the caller (not Uncle Tom himself)
4. Someone asking for money/help IS the caller (not the elderly person)
5. Look at the FLOW: who initiates topics vs. who responds

Output format:
Return ONLY a JSON object with a single field "labels".
Each label MUST be exactly "user" or "pottential_scammer".

Example (for 4 messages):
{
  "labels": ["user", "pottential_scammer", "user", "pottential_scammer"]
}
"""

    entries_text = "\n".join(
        f"Entry {idx}: \"{transcript[idx].get('text','')}\""
        for idx in indices_to_identify
    )

    user_prompt = f"""Analyze this phone conversation:

{conversation_text}

---
Now identify the speaker for each of these entries:
{entries_text}

---
REMEMBER - Only two possible labels:
- "user" = the elderly person (Uncle Tom, who answered the phone)
- "pottential_scammer" = the caller (Daniel, who called Uncle Tom)

Examples:
- "Hello? Who is this?" → "user" (answering the phone)
- "Hi Uncle Tom, it's Daniel" → "pottential_scammer" (caller identifying himself)
- "Oh Daniel! What a surprise!" → "user" (Uncle Tom responding)
- "I need money" / "Can you help me?" → "pottential_scammer" (making request)
- "That sounds suspicious" → "user" (elderly person being cautious)

Return ONLY this JSON format (each label must be "user" OR "pottential_scammer"):
{{
  "labels": ["user", "pottential_scammer", "user", ...]
}}

The number of labels MUST equal {len(indices_to_identify)}, in the same order as the entries above.
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
