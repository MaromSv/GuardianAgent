from typing import List, Dict, Any
import os
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
    Identify speakers in transcript, distinguishing between:
    - "user" (elderly person being protected)
    - "caller" (potential scammer)
    - "guardian" (AI assistant - already labeled)
    
    Args:
        transcript: List of transcript entries with speaker labels from LiveKit
                   Format: [{"speaker": "user"|"assistant"|"guardian", "text": "..."}]
        user_number: Phone number of the elderly person (optional, for context)
        caller_number: Phone number of the potential scammer (optional, for context)
        
    Returns:
        Updated transcript with proper speaker labels: "user"|"caller"|"guardian"
    """
    if not transcript:
        return transcript
    
    # Entries that already have "guardian" label don't need relabeling
    # Entries with "assistant" should become "guardian"
    # Entries with "user" need to be identified as either "user" (elderly) or "caller" (scammer)
    
    # First pass: Fix assistant → guardian mapping
    transcript = [
        {**entry, "speaker": "guardian"} if entry.get("speaker") == "assistant" else entry
        for entry in transcript
    ]
    
    # Find entries that need speaker identification (currently labeled as "user")
    needs_identification = [
        i for i, entry in enumerate(transcript)
        if entry.get("speaker") == "user" and "role" not in entry  # Exclude LiveKit metadata
    ]
    
    if not needs_identification:
        return transcript  # All speakers already identified
    
    # Use LLM to identify speakers in batch
    try:
        identified_speakers = _identify_speakers_with_llm(
            transcript, 
            needs_identification,
            user_number,
            caller_number
        )
        
        # Update transcript with identified speakers
        updated_transcript = transcript.copy()
        for idx, speaker_label in zip(needs_identification, identified_speakers):
            updated_transcript[idx] = {
                **updated_transcript[idx],
                "speaker": speaker_label
            }
        
        return updated_transcript
        
    except Exception as e:
        print(f"Error identifying speakers with LLM: {e}")
        # Fallback: Use simple heuristic
        return _fallback_speaker_identification(transcript, needs_identification)


def _identify_speakers_with_llm(
    transcript: List[Dict[str, str]],
    indices_to_identify: List[int],
    user_number: str = None,
    caller_number: str = None,
) -> List[str]:
    """
    Use LLM to identify speakers based on conversation context.
    
    Returns list of speaker labels ("user" or "caller") for each index in indices_to_identify.
    """
    client = _get_openai_client()
    
    # Build conversation context (last 10 messages for context)
    context_window = transcript[-10:] if len(transcript) > 10 else transcript
    conversation_text = "\n".join([
        f"[{i}] {entry.get('speaker', 'unknown').upper()}: {entry.get('text', '')}"
        for i, entry in enumerate(context_window)
    ])
    
    # Build prompt
    system_prompt = """You are analyzing a phone conversation to identify speakers.

**Context:**
- "user" = The elderly person being protected (likely answers questions, sounds uncertain, or confused)
- "caller" = The person who initiated the call (likely asking questions, making claims, requesting information)
- "guardian" = AI assistant protecting the user (asks verification questions)

**Task:**
Identify which entries are the "user" (elderly person) vs "caller" (person who called them).

**Clues:**
- Caller typically: makes claims about being from a company, creates urgency, requests sensitive info
- User typically: responds to questions, sounds reactive, asks for clarification
- Guardian: asks verification questions, requests proof

Output ONLY a JSON array of labels in order, one per unidentified entry.
Example: ["caller", "user", "caller", "user"]
"""
    
    # Build list of entries needing identification
    entries_text = "\n".join([
        f"Entry {idx}: \"{transcript[idx].get('text', '')}\""
        for idx in indices_to_identify
    ])
    
    user_prompt = f"""Full conversation context:
{conversation_text}

Entries needing identification:
{entries_text}

Output JSON array of labels ["user" or "caller"] for each entry in order."""
    
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3,  # Lower temperature for more consistent identification
        max_tokens=200,
    )
    
    # Parse response
    import json
    result_text = response.choices[0].message.content.strip()
    result_json = json.loads(result_text)
    
    # Extract labels array
    if isinstance(result_json, dict):
        labels = result_json.get("labels", result_json.get("speakers", []))
    else:
        labels = result_json
    
    # Validate labels
    labels = [
        label if label in ["user", "caller"] else "caller"  # Default to caller if uncertain
        for label in labels[:len(indices_to_identify)]
    ]
    
    # Pad if needed
    while len(labels) < len(indices_to_identify):
        labels.append("caller")
    
    return labels


def _fallback_speaker_identification(
    transcript: List[Dict[str, str]],
    indices_to_identify: List[int],
) -> List[Dict[str, str]]:
    """
    Fallback heuristic-based speaker identification when LLM is unavailable.
    
    Simple rule: First speaker is usually the caller, responses are usually the user.
    """
    updated_transcript = transcript.copy()
    
    # Find first unidentified entry - assume it's the caller
    first_unidentified = indices_to_identify[0] if indices_to_identify else None
    
    for idx in indices_to_identify:
        # Simple heuristic: alternate speakers, starting with caller
        if idx == first_unidentified:
            speaker = "caller"  # First speaker is usually the caller
        else:
            # Look at previous entry
            prev_speaker = updated_transcript[idx - 1].get("speaker") if idx > 0 else None
            if prev_speaker == "caller":
                speaker = "user"
            elif prev_speaker == "user":
                speaker = "caller"
            else:
                speaker = "caller"  # Default
        
        updated_transcript[idx] = {
            **updated_transcript[idx],
            "speaker": speaker
        }
    
    return updated_transcript


def needs_speaker_identification(transcript: List[Dict[str, str]]) -> bool:
    """
    Check if transcript has any entries needing speaker identification.
    
    Returns True if there are "user" entries without proper labels.
    """
    return any(
        entry.get("speaker") == "user" and "role" not in entry
        for entry in transcript
    )

