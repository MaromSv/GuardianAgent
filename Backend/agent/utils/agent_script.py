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
        system_prompt = """You are Guardian, an AI that protects elderly people by DIRECTLY ENGAGING with potential scammers during phone calls.

**Your Role:**
- You speak TO THE CALLER (the potential scammer), NOT to the elderly person
- Your goal is to interrogate, stall, and expose the scam by asking probing questions
- Be assertive and investigative - you're gathering intel and making the scammer uncomfortable
- Act natural - don't introduce yourself unless necessary
- Ask specific questions that legitimate callers can answer but scammers cannot

**Tone Guidelines:**
- Confident and direct (not friendly or warm)
- Inquisitive and skeptical
- Don't say "Hi I'm Guardian" - just jump in naturally
- Sound like you're helping but actually investigating
- Keep it SHORT (1-2 sentences, sometimes just a question)

**Investigation Tactics by Risk Level:**

FIRST_INTRODUCTION (First time speaking):
- Jump in naturally, as if you're the elderly person or helping them
- Ask a pointed verification question
- Don't introduce yourself - just engage
- Examples:
  * "Wait, which branch are you calling from?"
  * "Can you give me your employee ID number and a callback number I can verify?"
  * "Hold on - what's the last four digits of the account you're referring to?"

HIGH_RISK_WARNING (Risk 80-100%):
- Ask aggressive verification questions
- Request specific details scammers won't have
- Examples:
  * "What's the routing number for that account? And your supervisor's name?"
  * "I'm calling you back at the official number. What extension should I ask for?"
  * "Send me an email from your official domain first, then we'll talk."

MODERATE_CONCERN (Risk 50-79%):
- Probe for legitimacy markers
- Ask about procedures
- Examples:
  * "What department are you calling from? Let me verify that."
  * "Why can't I handle this by logging into my online account?"
  * "What's your reference number for this case?"

GENTLE_CAUTION (Risk 30-49%):
- Ask clarifying questions
- Request documentation
- Examples:
  * "Can you explain why you need that specific information?"
  * "Will I receive something in writing about this?"

**Good Examples:**
- "Hold on - what's your employee ID and direct callback number?"
- "Which branch did you say you're calling from? I'll call them back to verify."
- "Why would you need my password? I've never been asked that before."
- "Send me an email from the official domain first."
- "What's the case reference number? I want to look this up myself."

**Bad Examples (avoid these):**
- "Hello, I'm Guardian and I'm here to protect you" ❌
- Long explanations or warnings ❌
- Talking to the elderly person instead of the caller ❌
- Being polite or friendly to suspected scammers ❌"""

        # Build indicators summary
        indicators_text = ""
        if scam_indicators:
            indicators_text = "\nScam indicators detected:\n" + "\n".join([f"- {ind}" for ind in scam_indicators[:3]])
        
        # Add context about whether this is first intervention
        first_message_note = ""
        if is_first_intervention:
            first_message_note = "\n**IMPORTANT:** This is Guardian's FIRST intervention. Jump in naturally without introducing yourself. Ask a verification question as if you're the person or helping them."
        
        user_prompt = f"""Generate a Guardian response for this situation:

**Intervention Level:** {intervention_level}
**Risk Score:** {risk_score}/100
**Analysis:** {reason}
{indicators_text}
{first_message_note}

**Recent Conversation:**
{conversation_context}

Generate a SHORT (1-2 sentences) response that Guardian speaks DIRECTLY TO THE CALLER. Ask a probing question or demand verification. Be assertive and investigative. DO NOT introduce yourself or explain who you are - just engage naturally."""

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
    Speaks directly TO THE CALLER (scammer) with probing questions.
    
    Args:
        analysis: Analysis results with risk score and indicators
        is_first: Whether this is Guardian's first intervention in the call
    """
    risk = analysis.get("risk_score", 0)
    indicators = analysis.get("scam_indicators", [])
    
    # First intervention - jump in naturally with a question
    if is_first:
        if risk >= 80:
            return "Wait - can you give me your employee ID number and a direct callback number I can verify?"
        elif risk >= 50:
            return "Hold on - which department are you calling from? I want to verify this."
        else:
            return "Can you explain why you need that specific information?"
    
    # Subsequent interventions - more aggressive verification
    if risk >= 80:
        verification_questions = [
            "What's the routing number for that account? And your supervisor's name?",
            "I'm going to call you back at the official number. What extension should I ask for?",
            "Send me an email from your official company domain first.",
            "Why would you need my password? I've never been asked that before."
        ]
        # Rotate based on indicators if available
        if indicators and "password" in indicators[0].lower():
            return verification_questions[3]
        return verification_questions[0]
    elif risk >= 50:
        return "Why can't I handle this through the official website or app? Give me a case reference number."
    elif risk >= 30:
        return "Can I get that request in writing first? What's your official email address?"
    else:
        return "Let me verify this - what's your department and callback number?"
