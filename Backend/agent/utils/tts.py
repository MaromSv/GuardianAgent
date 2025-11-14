import uuid


def placeholder_text_to_speech(text: str) -> str:
    """
    Stub for ElevenLabs TTS.
    Return a fake URL or ID where the generated audio would live.
    """
    # In real implementation, you'd call ElevenLabs and store the audio somewhere.
    # For now just return a dummy URL string.
    fake_url = f"https://example.com/audio/{uuid.uuid4()}.mp3"
    print(f"[TTS] Would generate audio for: {text!r} -> {fake_url}")
    return fake_url
