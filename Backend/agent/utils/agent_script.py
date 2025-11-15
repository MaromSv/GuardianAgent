from typing import Any, Dict, List
import os
from openai import OpenAI


# Initialize OpenAI client (will use OPENAI_API_KEY from environment)
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


def generate_guardian_message(
    transcript: List[Dict[str, str]],
    analysis: Dict[str, Any],
) -> str:
    """
    Generate a natural, elderly-friendly intervention message using AI.
    
    The Guardian speaks directly to the elderly person in a calm, reassuring manner.
    Messages are designed to be clear, non-alarming, and actionable.
    
    Args:
        transcript: Conversation history
        analysis: Analysis results with risk score and scam indicators
        
    Returns:
        Guardian intervention message as a string
    """
    try:
        client = _get_openai_client()
        
        # Extract key information
        risk_score = analysis.get("risk_score", 0)
        scam_indicators = analysis.get("scam_indicators", [])
        reason = analysis.get("reason", "")
        
        # Check if this is Guardian's first intervention (no previous guardian messages)
        has_spoken_before = any(entry.get("speaker") == "guardian" for entry in transcript)
        is_first_intervention = not has_spoken_before
        
        # Format recent conversation context (last 3 messages)
        recent_transcript = transcript[-3:] if len(transcript) > 3 else transcript
        conversation_context = "\n".join([
            f"{entry['speaker'].upper()}: {entry['text']}"
            for entry in recent_transcript
        ])
        
        # Determine intervention level
        if is_first_intervention:
            # First time speaking - always use gentle introduction
            intervention_level = "FIRST_INTRODUCTION"
        elif risk_score >= 80:
            intervention_level = "HIGH_RISK_WARNING"
        elif risk_score >= 50:
            intervention_level = "MODERATE_CONCERN"
        else:
            intervention_level = "GENTLE_CAUTION"
        
        # Create the prompt
        system_prompt = """You are Guardian, an AI assistant helping verify phone call legitimacy for an elderly person.

**Role:** Speak TO THE CALLER. Ask polite but firm verification questions that legitimate callers can easily answer.

**Tone:** Professional, calm, brief (1-2 sentences). Like a helpful family member. Don't introduce yourself.

**Approach by Risk:**
- FIRST_INTRODUCTION: Jump in naturally with a verification question
- HIGH_RISK (80-100%): Request specific verification (employee ID, callback number, official email)
- MODERATE (50-79%): Ask about department, reference numbers, why this can't be handled online
- GENTLE (30-49%): Ask clarifying questions, request documentation

**Key:** Stay professional, never hostile. Ask questions, don't accuse."""

        # Build indicators summary
        indicators_text = ""
        if scam_indicators:
            indicators_text = "\nScam indicators detected:\n" + "\n".join([f"- {ind}" for ind in scam_indicators[:3]])
        
        # Add context about whether this is first intervention
        first_note = "FIRST intervention - jump in naturally." if is_first_intervention else ""
        
        user_prompt = f"""Level: {intervention_level} | Risk: {risk_score}/100
{reason}
{indicators_text}
{first_note}

Recent conversation:
{conversation_context}

Generate 1-2 sentence verification question to the caller. Professional, polite, firm. Don't introduce yourself."""

        # Call AI to generate message
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,  # Some creativity for natural speech
            max_tokens=150,  # Keep it short
        )
        
        # Extract the message
        message = response.choices[0].message.content.strip()
        
        # Remove quotes if AI wrapped the message
        if message.startswith('"') and message.endswith('"'):
            message = message[1:-1]
        if message.startswith("'") and message.endswith("'"):
            message = message[1:-1]
        
        return message
        
    except Exception as e:
        # Fallback to simple template-based message
        print(f"Error generating Guardian message with AI: {e}")
        return _fallback_guardian_message(analysis, is_first_intervention)


def _fallback_guardian_message(analysis: Dict[str, Any], is_first: bool = False) -> str:
    """
    Fallback message generator when AI is unavailable.
    Asks polite but firm verification questions to help the elderly person.
    
    Args:
        analysis: Analysis results with risk score and indicators
        is_first: Whether this is Guardian's first intervention in the call
    """
    risk = analysis.get("risk_score", 0)
    indicators = analysis.get("scam_indicators", [])
    
    # First intervention - polite verification request
    if is_first:
        if risk >= 80:
            return "Excuse me, could you provide your employee ID and a callback number we can verify?"
        elif risk >= 50:
            return "May I ask which department you're calling from? We'd like to verify that."
        else:
            return "Could you explain why you need that specific information?"
    
    # Subsequent interventions - firmer but still professional
    if risk >= 80:
        verification_questions = [
            "Could you provide your supervisor's name and direct line so we can verify?",
            "We'd prefer to call back at the official company number. What extension should we ask for?",
            "Could you send an email from your official company domain to confirm this?",
            "I'm not comfortable providing passwords over the phone. Is there another way to verify?"
        ]
        # Rotate based on indicators if available
        if indicators and "password" in indicators[0].lower():
            return verification_questions[3]
        return verification_questions[0]
    elif risk >= 50:
        return "Why can't this be handled through the online account? Could you provide a reference number?"
    elif risk >= 30:
        return "Could we get that request in writing? What's your official email address?"
    else:
        return "May I ask what department you're with and get a callback number?"
