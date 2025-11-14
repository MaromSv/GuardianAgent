from typing import Any, Dict, List


def placeholder_generate_guardian_message(
    transcript: List[Dict[str, str]],
    analysis: Dict[str, Any],
) -> str:
    """
    Stub for OpenAI-generated GuardianAgent speech.
    """
    risk = analysis.get("risk_score", 0)
    if risk >= 70:
        return (
            "This is GuardianAgent. This call seems risky. "
            "Please do not share any personal or banking information."
        )
    elif risk >= 40:
        return (
            "This is GuardianAgent. I have some concerns about this call. "
            "Could you please explain why you need this information?"
        )
    else:
        return (
            "This is GuardianAgent. I am monitoring this call. "
            "Please continue, but be cautious."
        )
