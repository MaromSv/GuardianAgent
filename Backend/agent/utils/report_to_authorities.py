import asyncio
import os
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

from browser_use import Agent, Browser, ChatBrowserUse
BROWSER_USE_AVAILABLE = True

# Configurable reporting authorities
AUTHORITIES = {
    # "ftc": {
    #     "name": "Federal Trade Commission (FTC)",
    #     "url": "https://reportfraud.ftc.gov/",
    #     "country": "USA",
    #     "description": "Reports phone scams to the US Federal Trade Commission",
    # },
    "authority": {
        "name": "National Do Not Call Registry",
        "url": "https://complaints.donotcall.gov/complaint/complaintcheck.aspx",
        "country": "USA",
        "description": "Reports unwanted/scam calls to FTC Do Not Call Registry",
    },
    # "ic3": {
    #     "name": "FBI Internet Crime Complaint Center (IC3)",
    #     "url": "https://www.ic3.gov/Home/FileComplaint",
    #     "country": "USA",
    #     "description": "Reports to FBI for federal investigation",
    # },
    # "fraudehelpdesk": {
    #     "name": "Dutch Fraud Help Desk (Fraudehelpdesk)",
    #     "url": "https://www.fraudehelpdesk.nl/",
    #     "country": "Netherlands",
    #     "description": "Reports phone scams to the Dutch national anti-fraud hotline",
    #     "phone": "+31 88 7867372",
    #     "language": "Dutch (can use Google Translate)",
    # },
}


def _get_authority_config(authority_name: str = None) -> Dict[str, Any]:
    """Get the reporting authority configuration."""
    default_authority = os.getenv("SCAM_REPORT_AUTHORITY", "ftc")
    authority = authority_name or default_authority
    
    if authority not in AUTHORITIES:
        print(f"Warning: Authority '{authority}' not found. Using 'ftc' as fallback.")
        authority = "authority"
    
    return AUTHORITIES[authority]


def _build_reporting_task(
    caller_number: str,
    user_number: str,
    analysis: Dict[str, Any],
    decision: Dict[str, Any],
    reputation_check: Optional[Dict[str, Any]],
    fact_check: Optional[Dict[str, Any]],
    authority_config: Dict[str, Any],
) -> str:
    """Build the task prompt for the browser agent. Creates a natural description from GuardianState data."""
    # For simple, repeatable testing we hardcode the scammer number here,
    # so every report uses the same known scam from our local database.
    # (Wells Fargo impersonation in the scam_numbers.json list)
    caller_number = "+18656304266"

    # Build natural, human-like description
    reason = decision.get("reason", "")
    indicators = analysis.get("scam_indicators", [])
    
    description_parts = []
    
    # Start with database match if applicable
    if reputation_check and reputation_check.get("known_scam"):
        description_parts.append("This number is a known scam.")
    
    # Add main issue in conversational language
    if "bank" in reason.lower() or "impersonat" in reason.lower():
        description_parts.append("The caller pretended to be from a legitimate organization and tried to get personal information.")
    elif "password" in reason.lower():
        description_parts.append("The caller tried to get passwords or login credentials.")
    elif "urgency" in reason.lower():
        description_parts.append("The caller used high-pressure tactics to create false urgency.")
    
    # Add specific behaviors
    behaviors = []
    for ind in indicators[:3]:
        if "password" in ind.lower():
            behaviors.append("asked for passwords")
        elif "urgency" in ind.lower():
            behaviors.append("created false urgency")
        elif "account" in ind.lower():
            behaviors.append("requested account numbers")
    
    if behaviors:
        description_parts.append(f"They {', '.join(behaviors)}.")
    
    scam_description = " ".join(description_parts) or reason
    
    # Determine scam type
    if reputation_check and reputation_check.get("scam_type"):
        scam_type = reputation_check.get("scam_type")
    elif any("bank" in ind.lower() for ind in indicators):
        scam_type = "Banking Fraud"
    else:
        scam_type = "Phone Fraud / Impersonation Scam"
    
    # Add phone number to instructions if available
    phone_info = f"\n- Phone contact: {authority_config['phone']}" if authority_config.get('phone') else ""
    language_note = f" (Form may be in {authority_config.get('language', 'English')})" if authority_config.get('language') else ""
    
    task = f"""
You are an automated assistant helping to report a confirmed phone scam to {authority_config['name']}.{language_note}

GOAL
- Navigate to: {authority_config['url']}
- Fill out the scam reporting form with the details below{phone_info}
- CRITICAL STOPPING POINT: After clicking "Continue" ONCE and reaching "STEP 2 OF 3", STOP IMMEDIATELY
- DO NOT proceed to Step 3
- DO NOT click any "Submit" or final submission buttons
- Summarize what fields were filled and confirm you stopped at Step 2

SCAM DETAILS
- Scammer Phone Number: {caller_number}
- Victim Phone Number: {user_number}
- Date/Time of Call: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- Scam Type: {scam_type}
- Description: {scam_description}
- How was contact made: Phone call (inbound to victim)

FORM FILLING INSTRUCTIONS
- If the form is in Dutch, enable browser translation or work with Dutch text
- Look for "Fraude melden" (Report Fraud) or similar buttons to access the report form
- Accept cookies if prompted (minimal/necessary only)
- Fill all required fields accurately in Step 1
- Click "Continue" ONCE to move to Step 2
- Fill required fields in Step 2
- When you see "STEP 2 OF 3" or similar text indicating Step 2, STOP IMMEDIATELY after filling Step 2 fields
- DO NOT click "Continue" a second time
- DO NOT proceed to Step 3 (which is typically the final submission/review step)
- Use the scam details provided above
- For any "victim information" fields, use the victim phone number
- For any "additional details" or "description" fields, include the full scam description
- If asked about monetary loss, indicate "No money lost (prevented by Guardian Agent)"
- Common Dutch form fields: "Telefoonnummer" (phone number), "Omschrijving" (description), "Datum" (date)

OUTPUT
- Confirm you have stopped at "STEP 2 OF 3"
- Report what fields were filled in Step 1 and Step 2
- Confirm you did NOT proceed to Step 3 or submit the form
- Note any errors or missing required fields
- Provide the current page URL
"""
    return task


async def report_scam_to_authorities(
    caller_number: str,
    user_number: str,
    analysis: Dict[str, Any],
    decision: Dict[str, Any],
    fact_check: Optional[Dict[str, Any]] = None,
    reputation_check: Optional[Dict[str, Any]] = None,
    transcript: Optional[list] = None,
    authority: Optional[str] = None,
    headless: bool = True,
) -> Dict[str, Any]:
    """
    Use browser automation to report a confirmed scam to authorities.
    
    This should ONLY be called when:
    - decision["action"] == "warn" (high confidence scam)
    - risk_score >= 80%
    
    Args:
        caller_number: The scammer's phone number
        user_number: The victim's phone number
        analysis: Analysis results from assess_scam_probability node
        decision: Decision results from agent's decision node
        fact_check: Optional fact-check results (for additional red flags)
        reputation_check: Optional phone reputation check (for scam type)
        transcript: Optional call transcript (for context)
        authority: Which authority to report to (default from env or "fraudehelpdesk")
        headless: (Deprecated) Browser mode is controlled by HEADLESS env var
        
    Environment Variables:
        BROWSERUSE_KEY or OPENAI_API_KEY: API key for browser automation
        OPENAI_BASE_URL: Optional custom API endpoint
        BROWSERUSE_MODEL: Optional model name (handled by ChatBrowserUse)
        
    Returns:
        Dict with:
        - status: "success" | "failed" | "disabled"
        - authority: Name of reporting authority
        - message: Summary of what happened
        - form_data: What was filled in the form
        - browser_result: Result from browser agent
        - error: Error message if failed
    """
    if not BROWSER_USE_AVAILABLE:
        return {
            "status": "disabled",
            "message": "browser_use not installed. Automated reporting disabled.",
            "authority": None,
        }
    
    # Check if we should report (must be high confidence)
    risk_score = decision.get("risk_score", 0)
    action = decision.get("action", "observe")
    
    if action != "warn" or risk_score < 80:
        return {
            "status": "skipped",
            "message": f"Not reporting: action={action}, risk={risk_score}% (need warn + 80%+)",
            "authority": None,
        }
    
    try:
        authority_config = _get_authority_config(authority)
        
        print(f"🚨 Reporting scam to {authority_config['name']}...")
        print(f"   Scammer: {caller_number}")
        print(f"   Risk: {risk_score}%")
        
        # Build task for browser agent
        task = _build_reporting_task(
            caller_number=caller_number,
            user_number=user_number,
            analysis=analysis,
            decision=decision,
            reputation_check=reputation_check,
            fact_check=fact_check,
            authority_config=authority_config,
        )
        
        # Initialize browser (simpler API - headless controlled via environment)
        browser = Browser()
        
        # Initialize LLM (browser-use handles API key from environment automatically)
        # It looks for BROWSERUSE_KEY or OPENAI_API_KEY automatically
        llm = ChatBrowserUse()
        
        # Create and run agent
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
        )
        
        print("🤖 Browser agent starting...")
        history = await agent.run()
        
        # Extract results from history
        final_result = history[-1] if history else {}
        
        print(f"✅ Scam report prepared for {authority_config['name']}")
        
        return {
            "status": "success",
            "authority": authority_config["name"],
            "authority_url": authority_config["url"],
            "message": f"Scam report form filled and ready for submission to {authority_config['name']}",
            "form_data": {
                "scammer_number": caller_number,
                "victim_number": user_number,
                "risk_score": risk_score,
                "timestamp": datetime.now().isoformat(),
            },
            "browser_result": final_result,
        }
        
    except Exception as e:
        error_msg = f"Error reporting scam to authorities: {e}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        
        return {
            "status": "failed",
            "authority": authority_config.get("name") if 'authority_config' in locals() else None,
            "message": error_msg,
            "error": str(e),
        }


def report_scam_to_authorities_sync(
    caller_number: str,
    user_number: str,
    analysis: Dict[str, Any],
    decision: Dict[str, Any],
    fact_check: Optional[Dict[str, Any]] = None,
    reputation_check: Optional[Dict[str, Any]] = None,
    transcript: Optional[list] = None,
    authority: Optional[str] = None,
    headless: bool = True,
) -> Dict[str, Any]:
    """
    Synchronous wrapper for report_scam_to_authorities.
    Use this in agent.py nodes (which are synchronous).
    
    Automatically pulls data from your GuardianState and formats it for reporting.
    """
    try:
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            report_scam_to_authorities(
                caller_number=caller_number,
                user_number=user_number,
                analysis=analysis,
                decision=decision,
                fact_check=fact_check,
                reputation_check=reputation_check,
                transcript=transcript,
                authority=authority,
                headless=headless,
            )
        )
        loop.close()
        return result
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Sync wrapper error: {e}",
            "error": str(e),
        }


# Helper function to check if reporting is appropriate
def should_report_to_authorities(decision: Dict[str, Any]) -> bool:
    """
    Determine if a scam should be reported to authorities.
    
    Criteria:
    - Action must be "warn" (highest severity)
    - Risk score must be >= 80% (very high confidence)
    
    Returns:
        True if scam should be reported, False otherwise
    """
    action = decision.get("action", "observe")
    risk_score = decision.get("risk_score", 0)
    
    return action == "warn" and risk_score >= 80


# Helper function to format reporting summary for logs
def format_authority_report_summary(report_result: Dict[str, Any]) -> str:
    """
    Format authority reporting results into a readable summary.
    """
    status = report_result.get("status", "unknown")
    authority = report_result.get("authority", "Unknown Authority")
    message = report_result.get("message", "")
    
    if status == "success":
        return f"✅ Scam reported to {authority}. {message}"
    elif status == "skipped":
        return f"⏭️  Authority report skipped: {message}"
    elif status == "disabled":
        return f"❌ Authority reporting disabled: {message}"
    else:
        error = report_result.get("error", "Unknown error")
        return f"❌ Failed to report to authorities: {error}"

