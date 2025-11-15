from typing import List, Dict, Any
import os
import json
from openai import OpenAI
from pydantic import BaseModel, Field, validator


# Initialize OpenAI client (will use OPENAI_API_KEY from environment)
_client = None


class ScamAnalysisResponse(BaseModel):
    """
    Pydantic model for validating LLM response structure.
    Ensures risk_score and confidence are always proper numeric types.
    """
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Risk score from 0-100")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level from 0.0-1.0")
    reason: str = Field(..., min_length=1, description="Explanation of the assessment")
    scam_indicators: List[str] = Field(default_factory=list, description="List of detected scam indicators")
    recommended_action: str = Field(..., description="Recommended action: observe, question, or warn")
    
    @validator('risk_score', pre=True)
    def validate_risk_score(cls, v):
        """Ensure risk_score is a valid number and within range."""
        try:
            score = float(v)
            if score < 0.0:
                return 0.0
            if score > 100.0:
                return 100.0
            return score
        except (ValueError, TypeError):
            raise ValueError(f"risk_score must be a number between 0-100, got: {v}")
    
    @validator('confidence', pre=True)
    def validate_confidence(cls, v):
        """Ensure confidence is a valid number and within range."""
        try:
            conf = float(v)
            if conf < 0.0:
                return 0.0
            if conf > 1.0:
                return 1.0
            return conf
        except (ValueError, TypeError):
            raise ValueError(f"confidence must be a number between 0.0-1.0, got: {v}")
    
    @validator('recommended_action')
    def validate_action(cls, v):
        """Ensure recommended_action is one of the valid options."""
        valid_actions = ["observe", "question", "warn"]
        if v.lower() not in valid_actions:
            # Default to "observe" if invalid
            print(f"Warning: Invalid action '{v}', defaulting to 'observe'")
            return "observe"
        return v.lower()


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


def analyze_transcript(transcript: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Analyze conversation transcript for scam indicators using OpenAI.
    
    Args:
        transcript: List of conversation turns with 'speaker' and 'text'
        
    Returns:
        Dict with risk_score (0-100), confidence (0-1), and detailed analysis
    """
    if not transcript:
        return {
            "risk_score": 0.0,
            "confidence": 0.0,
            "reason": "No transcript to analyze",
            "scam_indicators": [],
        }
    
    try:
        client = _get_openai_client()
        
        # Format transcript for analysis
        formatted_transcript = "\n".join([
            f"{entry['speaker'].upper()}: {entry['text']}"
            for entry in transcript
        ])
        
        # Construct the analysis prompt
        system_prompt = """You are an expert fraud detection AI that analyzes phone conversations to identify potential scams targeting vulnerable individuals, especially elderly people.

Your job is to analyze the conversation transcript and assess the likelihood of fraud based on common scam tactics:

**Common Scam Indicators:**
1. Urgency/pressure tactics ("act now", "limited time")
2. Requests for sensitive information (passwords, SSN, account numbers)
3. Impersonation of authority (banks, government, tech support)
4. Requests for payment via gift cards, wire transfer, cryptocurrency
5. Threats or fear tactics (account frozen, legal action)
6. Too-good-to-be-true offers (prizes, inheritance, refunds)
7. Requests to keep conversation secret
8. Inconsistencies in caller's story
9. Requests to bypass normal security procedures
10. Pressure to make immediate decisions

**Analysis Guidelines:**
- Risk Score: 0-100 (0=completely safe, 100=definite scam)
- Confidence: 0.0-1.0 (how certain you are of your assessment)
- Be especially vigilant for tactics targeting elderly or vulnerable people
- Consider context: legitimate businesses don't ask for passwords or pressure immediate payment
- Multiple indicators = higher risk

Respond ONLY with valid JSON in this exact format:
{
  "risk_score": <number 0-100>,
  "confidence": <number 0.0-1.0>,
  "reason": "<brief explanation of your assessment>",
  "scam_indicators": ["<indicator 1>", "<indicator 2>", ...],
  "recommended_action": "observe|question|warn"
}"""

        user_prompt = f"""Analyze this phone conversation for scam indicators:

{formatted_transcript}

Provide your fraud risk assessment as JSON."""

        # Call OpenAI API (or Featherless, etc.)
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,  # Configurable via .env
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=500,
            response_format={"type": "json_object"}  # Ensure JSON response
        )
        
        # Parse the response
        result_text = response.content.strip() if hasattr(response, 'content') else response.choices[0].message.content.strip()
        result_json = json.loads(result_text)
        
        # Validate using Pydantic model (ensures proper types and ranges)
        try:
            validated = ScamAnalysisResponse(**result_json)
            
            return {
                "risk_score": validated.risk_score,
                "confidence": validated.confidence,
                "reason": validated.reason,
                "scam_indicators": validated.scam_indicators,
                "recommended_action": validated.recommended_action,
                "model": model,  # Return the actual model used
            }
        except Exception as validation_error:
            print(f"Pydantic validation error: {validation_error}")
            # If validation fails, use fallback with safe defaults
            return {
                "risk_score": float(result_json.get("risk_score", 0.0)),
                "confidence": max(0.0, min(1.0, float(result_json.get("confidence", 0.5)))),
                "reason": result_json.get("reason", "AI-based transcript analysis completed"),
                "scam_indicators": result_json.get("scam_indicators", []),
                "recommended_action": result_json.get("recommended_action", "observe"),
                "model": model,
            }
        
    except ValueError as e:
        # API key not set
        print(f"OpenAI API error: {e}")
        return _fallback_analysis(transcript)
        
    except Exception as e:
        # OpenAI API error or other issue - fallback to simple heuristic
        print(f"Error during OpenAI analysis: {e}")
        return _fallback_analysis(transcript)


def _fallback_analysis(transcript: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Fallback analysis using simple keyword heuristics when OpenAI is unavailable.
    This is the old placeholder logic, kept as a backup.
    """
    full_text = " ".join([t["text"] for t in transcript])
    
    scam_keywords = {
        "bank": 20,
        "password": 30,
        "social security": 40,
        "ssn": 40,
        "gift card": 35,
        "wire transfer": 35,
        "account number": 25,
        "verify your identity": 20,
        "suspended": 25,
        "frozen": 25,
        "urgent": 15,
        "immediately": 15,
        "act now": 20,
    }
    
    base_risk = 10.0
    found_indicators = []
    
    for keyword, risk_increase in scam_keywords.items():
        if keyword.lower() in full_text.lower():
            base_risk += risk_increase
            found_indicators.append(keyword)
    
    base_risk = min(base_risk, 100.0)
    confidence = min(base_risk / 100.0, 0.7)  # Lower confidence for fallback
    
    return {
        "risk_score": base_risk,
        "confidence": confidence,
        "reason": "Fallback keyword-based analysis (OpenAI unavailable)",
        "scam_indicators": found_indicators,
        "recommended_action": "warn" if base_risk >= 80 else ("question" if base_risk >= 40 else "observe"),
        "model": "fallback-heuristic",
    }
