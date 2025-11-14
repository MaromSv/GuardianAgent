from typing import Any, Dict


def placeholder_check_reputation(phone_number: str) -> Dict[str, Any]:
    """
    Stub for scam DB lookup.
    Replace with real DB lookups later.
    """
    # Dummy logic: treat numbers ending with '9999' as risky
    risk = 90.0 if phone_number.endswith("9999") else 5.0
    known = phone_number.endswith("9999")
    return {
        "phone_number": phone_number,
        "risk_score": risk,
        "known_scam": known,
        "source": "placeholder_db",
    }
