from typing import List, Dict, Any


def placeholder_analyze_transcript(transcript: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Stub for OpenAI-based scam analysis.
    Replace with real LLM call later.
    """
    full_text = " ".join([t["text"] for t in transcript])
    # Dummy heuristic: if certain words appear, bump risk.
    low_keywords = ["hello", "how are you"]
    scam_keywords = ["bank", "transfer", "password", "social security", "gift card"]

    base_risk = 10.0
    for kw in scam_keywords:
        if kw.lower() in full_text.lower():
            base_risk += 30.0

    base_risk = min(base_risk, 100.0)
    confidence = min(base_risk / 100.0, 1.0)

    return {
        "risk_score": base_risk,
        "confidence": confidence,
        "reason": "placeholder analysis based on simple keyword heuristic",
    }
