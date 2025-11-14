"""
Utility to report and save scam numbers to the local database.
"""
from typing import Dict, Any
import json
from pathlib import Path
from datetime import datetime


def _normalize_number(phone_number: str) -> str:
    """
    Normalize phone number by removing all non-digit characters.
    """
    return ''.join(c for c in phone_number if c.isdigit())


def add_scam_to_database(
    phone_number: str,
    risk_score: float,
    analysis: Dict[str, Any],
    decision: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add a detected scam number to the local scam database.
    
    Args:
        phone_number: The scam phone number to add
        risk_score: Risk score from analysis (0-100)
        analysis: Analysis results with scam indicators
        decision: Decision object with action details
        
    Returns:
        Dict with success status and details
    """
    try:
        # Get path to scam database
        current_dir = Path(__file__).parent
        json_path = current_dir / "scam_numbers.json"
        
        # Load existing database
        try:
            with open(json_path, 'r') as f:
                scam_db = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Scam database not found at {json_path}, creating new one")
            scam_db = []
        except Exception as e:
            print(f"Error loading scam database: {e}")
            return {
                "success": False,
                "error": f"Failed to load database: {e}"
            }
        
        # Check if number already exists
        normalized = _normalize_number(phone_number)
        for entry in scam_db:
            if _normalize_number(entry["number"]) == normalized:
                return {
                    "success": False,
                    "reason": "already_exists",
                    "message": f"Number {phone_number} already in database"
                }
        
        # Generate note from analysis
        scam_indicators = analysis.get("scam_indicators", [])
        reason = analysis.get("reason", "Detected as scam by AI analysis")
        
        if scam_indicators:
            indicators_text = ", ".join(scam_indicators[:3])  # Top 3 indicators
            note = f"Detected scam (Risk: {risk_score:.0f}%). Indicators: {indicators_text}."
        else:
            note = f"Detected scam (Risk: {risk_score:.0f}%). {reason}"
        
        # Add timestamp info
        timestamp = datetime.now().strftime("%Y-%m-%d")
        note += f" [Auto-detected: {timestamp}]"
        
        # Create new entry
        new_entry = {
            "number": phone_number,
            "notes": note
        }
        
        # Add to database
        scam_db.append(new_entry)
        
        # Save updated database
        try:
            with open(json_path, 'w') as f:
                json.dump(scam_db, f, indent=2)
            
            print(f"✓ Added scam number to database: {phone_number}")
            
            return {
                "success": True,
                "phone_number": phone_number,
                "note": note,
                "database_size": len(scam_db),
                "message": f"Successfully added {phone_number} to scam database"
            }
            
        except Exception as e:
            print(f"Error saving scam database: {e}")
            return {
                "success": False,
                "error": f"Failed to save database: {e}"
            }
    
    except Exception as e:
        print(f"Unexpected error in add_scam_to_database: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_database_stats() -> Dict[str, Any]:
    """
    Get statistics about the scam database.
    
    Returns:
        Dict with database statistics
    """
    try:
        current_dir = Path(__file__).parent
        json_path = current_dir / "scam_numbers.json"
        
        with open(json_path, 'r') as f:
            scam_db = json.load(f)
        
        # Count auto-detected vs manual entries
        auto_detected = sum(1 for entry in scam_db if "[Auto-detected:" in entry.get("notes", ""))
        manual = len(scam_db) - auto_detected
        
        return {
            "total_numbers": len(scam_db),
            "auto_detected": auto_detected,
            "manual_entries": manual,
            "database_path": str(json_path)
        }
        
    except Exception as e:
        return {
            "error": str(e)
        }

