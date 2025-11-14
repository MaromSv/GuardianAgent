from typing import Any, Dict
import json
import os
from pathlib import Path


# Load scam database once at module import
_scam_db = None

def _load_scam_database():
    """Load the scam numbers database from JSON file."""
    global _scam_db
    if _scam_db is not None:
        return _scam_db
    
    # Get the path to the JSON file (same directory as this script)
    current_dir = Path(__file__).parent
    json_path = current_dir / "scam_numbers.json"
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            # Create a lookup dict with normalized numbers as keys
            _scam_db = {_normalize_number(entry["number"]): entry for entry in data}
            return _scam_db
    except FileNotFoundError:
        print(f"Warning: Scam database not found at {json_path}")
        _scam_db = {}
        return _scam_db
    except Exception as e:
        print(f"Error loading scam database: {e}")
        _scam_db = {}
        return _scam_db


def _normalize_number(phone_number: str) -> str:
    """
    Normalize phone number by removing all non-digit characters.
    Examples:
        "+1 (555) 123-4567" -> "15551234567"
        "555-123-4567" -> "5551234567"
        "+15551234567" -> "15551234567"
    """
    return ''.join(c for c in phone_number if c.isdigit())


def check_reputation(phone_number: str) -> Dict[str, Any]:
    """
    Check if a phone number exists in the known scam database.
    
    Args:
        phone_number: Phone number to check (any format)
        
    Returns:
        Dict with risk_score, known_scam status, and details
    """
    # Load database (cached after first call)
    scam_db = _load_scam_database()
    
    # Normalize the input number
    normalized = _normalize_number(phone_number)
    
    # Check if it's in the known scam database
    if normalized in scam_db:
        entry = scam_db[normalized]
        return {
            "phone_number": phone_number,
            "risk_score": 95.0,  # Very high risk for known scams
            "known_scam": True,
            "source": "local_scam_db",
            "scam_type": entry.get("notes", "Known scam number"),
            "database_match": True,
        }
    
    # If last 10 digits match (handles +1 prefix differences)
    if len(normalized) >= 10:
        last_10 = normalized[-10:]
        for db_number, entry in scam_db.items():
            if db_number.endswith(last_10) or last_10.endswith(db_number[-10:] if len(db_number) >= 10 else db_number):
                return {
                    "phone_number": phone_number,
                    "risk_score": 90.0,  # High risk (possible match)
                    "known_scam": True,
                    "source": "local_scam_db",
                    "scam_type": entry.get("notes", "Potential scam number"),
                    "database_match": True,
                    "match_type": "partial",
                }
    
    # Not in database - return low risk
    return {
        "phone_number": phone_number,
        "risk_score": 10.0,  # Low baseline risk
        "known_scam": False,
        "source": "local_scam_db",
        "database_match": False,
    }
