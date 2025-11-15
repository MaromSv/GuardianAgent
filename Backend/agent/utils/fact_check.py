"""
Fact-checking utility for validating claims made by callers.
Uses LLM to verify organizational policies, procedures, and common scam tactics.
"""
from typing import Dict, Any, List, Optional
import os
import json
from openai import OpenAI
from pydantic import BaseModel, Field, validator


# Pydantic models for validation
class FactCheckClaim(BaseModel):
    """Model for a single claim (verified or suspicious)."""
    claim: str
    verification: Optional[str] = None
    problem: Optional[str] = None
    reality: Optional[str] = None
    severity: Optional[str] = None
    
    @validator('severity')
    def validate_severity(cls, v):
        """Ensure severity is valid if provided."""
        if v is not None:
            valid_severities = ["high", "medium", "low"]
            if v.lower() not in valid_severities:
                return "medium"  # Default
            return v.lower()
        return v


class FactCheckResponse(BaseModel):
    """Pydantic model for validating fact-check LLM response."""
    verified_claims: List[FactCheckClaim] = Field(default_factory=list)
    suspicious_claims: List[FactCheckClaim] = Field(default_factory=list)
    risk_increase: float = Field(..., ge=0.0, le=50.0, description="Additional risk from fact-checking (0-50)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in fact-check results")
    summary: str = Field(..., min_length=1, description="Overall assessment summary")
    
    @validator('risk_increase', pre=True)
    def validate_risk_increase(cls, v):
        """Ensure risk_increase is a valid number within range."""
        try:
            risk = float(v)
            if risk < 0.0:
                return 0.0
            if risk > 50.0:
                return 50.0
            return risk
        except (ValueError, TypeError):
            raise ValueError(f"risk_increase must be a number between 0-50, got: {v}")
    
    @validator('confidence', pre=True)
    def validate_confidence(cls, v):
        """Ensure confidence is a valid number within range."""
        try:
            conf = float(v)
            if conf < 0.0:
                return 0.0
            if conf > 1.0:
                return 1.0
            return conf
        except (ValueError, TypeError):
            raise ValueError(f"confidence must be a number between 0.0-1.0, got: {v}")


# Initialize OpenAI client
_client = None

def _get_openai_client():
    """Lazy-load OpenAI client (supports OpenAI, Featherless, or any OpenAI-compatible API)."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set. "
                "Please add it to your .env file."
            )
        
        # Support custom base URL (for Featherless, etc.)
        base_url = os.getenv("OPENAI_BASE_URL")
        if base_url:
            _client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            _client = OpenAI(api_key=api_key)
    return _client


def fact_check_claims(transcript: List[Dict[str, str]], caller_number: str = None) -> Dict[str, Any]:
    """
    Fact-check claims made by the caller using LLM knowledge.
    
    This validates:
    - Organizational policies (e.g., "Banks never ask for passwords")
    - Common legitimate vs. scam practices
    - Contact method validity
    - Urgency tactics legitimacy
    
    Args:
        transcript: List of conversation messages
        caller_number: Optional phone number for additional context
        
    Returns:
        Dict with fact-check results including:
        - verified_claims: List of legitimate claims
        - suspicious_claims: List of illegitimate/suspicious claims
        - risk_increase: Additional risk score from fact-checking (0-50)
        - confidence: How confident the fact-checker is (0.0-1.0)
    """
    if not transcript or len(transcript) == 0:
        return {
            "verified_claims": [],
            "suspicious_claims": [],
            "risk_increase": 0,
            "confidence": 0.0,
            "note": "No conversation to fact-check"
        }
    
    try:
        client = _get_openai_client()
        
        # Extract only caller messages (what we're fact-checking)
        caller_messages = [
            entry["text"] for entry in transcript 
            if entry.get("speaker") == "caller"
        ]
        
        if not caller_messages:
            return {
                "verified_claims": [],
                "suspicious_claims": [],
                "risk_increase": 0,
                "confidence": 0.0,
                "note": "No caller messages to fact-check"
            }
        
        # Format caller's claims
        caller_text = "\n".join([f"- {msg}" for msg in caller_messages])
        
        # Construct the fact-checking prompt
        system_prompt = """You are an expert fact-checker specializing in identifying phone scams by validating claims against known organizational policies and legitimate business practices.

**Your Task:**
Analyze the caller's statements and identify:
1. Claims about their organization/identity
2. Requests for information or actions
3. Stated procedures or policies
4. Urgency or threat tactics

Then validate each claim against real-world knowledge of legitimate business practices.

**Common Legitimate Practices (RED FLAGS if violated):**
- Banks NEVER ask for passwords, PINs, or full account numbers over the phone
- IRS sends letters first, NEVER calls about payment
- Tech companies don't cold-call about viruses or support
- Government agencies don't threaten arrest over the phone
- Legitimate companies don't require gift card payments
- Official organizations give time to verify (days/weeks, not minutes)
- Real banks/companies encourage you to call them back at official numbers
- Wire transfers are NEVER required for verification or "security"
- SSN is NEVER required for random verification calls

**Urgency Red Flags:**
- "Account will be closed/locked in 24 hours"
- "Police will arrest you today"
- "Your computer is infected NOW"
- "Immediate payment required"
- "Don't hang up or verification fails"

Respond ONLY with valid JSON in this exact format:
{
  "verified_claims": [
    {
      "claim": "<what they said>",
      "verification": "<why this seems legitimate>"
    }
  ],
  "suspicious_claims": [
    {
      "claim": "<what they said>",
      "problem": "<why this is suspicious>",
      "reality": "<what legitimate practice actually is>",
      "severity": "high|medium|low"
    }
  ],
  "risk_increase": <number 0-50>,
  "confidence": <number 0.0-1.0>,
  "summary": "<brief overall assessment>"
}

**Risk Increase Guidelines:**
- 0-10: Minor inconsistencies, possibly legitimate
- 10-20: Some suspicious elements, needs verification
- 20-35: Multiple red flags, likely illegitimate
- 35-50: Blatant scam tactics, definitely illegitimate"""

        user_prompt = f"""Fact-check these caller statements:

{caller_text}

Validate each claim against known legitimate business practices. Identify any red flags or violations of standard organizational policies."""

        # Call LLM for fact-checking
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,  # Low temperature for factual analysis
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        result_text = response.choices[0].message.content.strip()
        result_json = json.loads(result_text)
        
        # Validate using Pydantic model (ensures proper types and ranges)
        try:
            validated = FactCheckResponse(**result_json)
            
            return {
                "verified_claims": [claim.dict() for claim in validated.verified_claims],
                "suspicious_claims": [claim.dict() for claim in validated.suspicious_claims],
                "risk_increase": validated.risk_increase,
                "confidence": validated.confidence,
                "summary": validated.summary,
                "model": model,
            }
        except Exception as validation_error:
            print(f"Pydantic validation error in fact-check: {validation_error}")
            # If validation fails, use safe defaults
            return {
                "verified_claims": result_json.get("verified_claims", []),
                "suspicious_claims": result_json.get("suspicious_claims", []),
                "risk_increase": max(0.0, min(50.0, float(result_json.get("risk_increase", 0)))),
                "confidence": max(0.0, min(1.0, float(result_json.get("confidence", 0.5)))),
                "summary": result_json.get("summary", "Fact-check completed"),
                "model": model,
            }
        
    except ValueError as e:
        # API key not set
        print(f"Fact-check error: {e}")
        return _fallback_fact_check(transcript)
        
    except Exception as e:
        # LLM error - fallback to rule-based checking
        print(f"Error during LLM fact-check: {e}")
        return _fallback_fact_check(transcript)


def _fallback_fact_check(transcript: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Fallback fact-checker using simple rule-based detection.
    Used when LLM is unavailable.
    """
    caller_messages = [
        entry["text"].lower() for entry in transcript 
        if entry.get("speaker") == "caller"
    ]
    
    if not caller_messages:
        return {
            "verified_claims": [],
            "suspicious_claims": [],
            "risk_increase": 0,
            "confidence": 0.0,
            "note": "Fallback fact-check: No caller messages"
        }
    
    caller_text = " ".join(caller_messages)
    
    # Rule-based red flags
    red_flags = [
        {
            "keywords": ["password", "pin code", "pin number"],
            "claim": "Requesting password or PIN",
            "problem": "Legitimate organizations never ask for passwords over the phone",
            "severity": "high",
            "risk": 25
        },
        {
            "keywords": ["social security number", "ssn"],
            "claim": "Requesting Social Security Number",
            "problem": "Random verification calls don't require SSN",
            "severity": "high",
            "risk": 20
        },
        {
            "keywords": ["gift card", "itunes card", "google play card", "steam card"],
            "claim": "Requesting gift card payment",
            "problem": "No legitimate business accepts gift cards as payment",
            "severity": "high",
            "risk": 30
        },
        {
            "keywords": ["wire transfer", "wire money", "western union", "moneygram"],
            "claim": "Requesting wire transfer",
            "problem": "Legitimate companies don't require immediate wire transfers",
            "severity": "high",
            "risk": 25
        },
        {
            "keywords": ["account number", "routing number", "bank account"],
            "claim": "Requesting full account details",
            "problem": "Banks already have your account info; they don't need to ask",
            "severity": "high",
            "risk": 20
        },
        {
            "keywords": ["froze", "frozen", "locked", "suspended"],
            "claim": "Claiming account is frozen/locked",
            "problem": "Banks send official written notice before freezing accounts",
            "severity": "medium",
            "risk": 15
        },
        {
            "keywords": ["24 hours", "immediately", "right now", "urgent"],
            "claim": "Creating artificial urgency",
            "problem": "Legitimate companies give reasonable time to respond",
            "severity": "medium",
            "risk": 10
        },
        {
            "keywords": ["arrest", "police", "warrant", "jail"],
            "claim": "Threatening arrest or legal action",
            "problem": "Legitimate agencies send official notices, don't threaten over phone",
            "severity": "high",
            "risk": 25
        },
        {
            "keywords": ["don't tell anyone", "keep this confidential", "don't hang up"],
            "claim": "Asking to keep call secret",
            "problem": "Legitimate businesses encourage verification through official channels",
            "severity": "medium",
            "risk": 15
        }
    ]
    
    suspicious_claims = []
    total_risk = 0
    
    for flag in red_flags:
        if any(keyword in caller_text for keyword in flag["keywords"]):
            suspicious_claims.append({
                "claim": flag["claim"],
                "problem": flag["problem"],
                "reality": "Legitimate organizations follow proper verification procedures",
                "severity": flag["severity"]
            })
            total_risk += flag["risk"]
    
    # Cap total risk increase
    risk_increase = min(total_risk, 50)
    confidence = 0.7 if suspicious_claims else 0.3  # Lower confidence for fallback
    
    return {
        "verified_claims": [],
        "suspicious_claims": suspicious_claims,
        "risk_increase": risk_increase,
        "confidence": confidence,
        "summary": f"Fallback fact-check: Found {len(suspicious_claims)} red flags",
        "model": "rule-based-fallback",
    }


# Helper function to format fact-check results for logging/display
def format_fact_check_report(fact_check_results: Dict[str, Any]) -> str:
    """
    Format fact-check results into a human-readable report.
    
    Args:
        fact_check_results: Results from fact_check_claims()
        
    Returns:
        Formatted string report
    """
    report = ["=== FACT-CHECK REPORT ==="]
    
    suspicious = fact_check_results.get("suspicious_claims", [])
    verified = fact_check_results.get("verified_claims", [])
    risk_increase = fact_check_results.get("risk_increase", 0)
    summary = fact_check_results.get("summary", "")
    
    if suspicious:
        report.append(f"\n⚠️  SUSPICIOUS CLAIMS DETECTED ({len(suspicious)}):")
        for i, claim in enumerate(suspicious, 1):
            severity = claim.get("severity", "unknown").upper()
            report.append(f"\n{i}. [{severity}] {claim.get('claim', 'Unknown claim')}")
            report.append(f"   Problem: {claim.get('problem', 'N/A')}")
            if claim.get("reality"):
                report.append(f"   Reality: {claim.get('reality')}")
    
    if verified:
        report.append(f"\n✓ Verified Claims ({len(verified)}):")
        for claim in verified:
            report.append(f"  - {claim.get('claim', 'Unknown')}")
    
    report.append(f"\nRisk Increase: +{risk_increase:.0f}%")
    report.append(f"Summary: {summary}")
    
    return "\n".join(report)

