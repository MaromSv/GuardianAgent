"""
Browser automation utility for reporting confirmed scam phone numbers to authorities.
Uses browser_use to automate form filling on official scam reporting websites.

This runs ONLY when we are 100% confident a call is a scam (action == 'warn').
"""
import asyncio
import os
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

try:
    from browser_use import Agent, Browser, Controller
    from langchain_openai import ChatOpenAI
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    print("Warning: browser_use not installed. Scam reporting to authorities will be disabled.")


# Configurable reporting authorities
AUTHORITIES = {
    "ftc": {
        "name": "Federal Trade Commission (FTC)",
        "url": "https://reportfraud.ftc.gov/",
        "country": "USA",
        "description": "Reports phone scams to the US Federal Trade Commission",
    },
    "ic3": {
        "name": "FBI Internet Crime Complaint Center (IC3)",
        "url": "https://www.ic3.gov/Home/FileComplaint",
        "country": "USA",
        "description": "Reports to FBI for federal investigation",
    },
    "donotcall": {
        "name": "National Do Not Call Registry",
        "url": "https://complaints.donotcall.gov/complaint/complaintcheck.aspx",
        "country": "USA",
        "description": "Reports unwanted/scam calls to FTC Do Not Call Registry",
    },
}


def _get_authority_config(authority_name: str = None) -> Dict[str, Any]:
    """Get the reporting authority configuration."""
    default_authority = os.getenv("SCAM_REPORT_AUTHORITY", "donotcall")
    authority = authority_name or default_authority
    
    if authority not in AUTHORITIES:
        print(f"Warning: Authority '{authority}' not found. Using 'donotcall' as fallback.")
        authority = "donotcall"
    
    return AUTHORITIES[authority]


def _build_reporting_task(
    caller_number: str,
    user_number: str,
    analysis: Dict[str, Any],
    decision: Dict[str, Any],
    fact_check: Optional[Dict[str, Any]],
    authority_config: Dict[str, Any],
) -> str:
    """
    Build the task prompt for the browser agent to report the scam.
    """
    risk_score = decision.get("risk_score", 0)
    reason = decision.get("reason", "High risk detected")
    scam_indicators = analysis.get("scam_indicators", [])
    
    # Extract suspicious claims if fact-check was run
    suspicious_claims = []
    if fact_check:
        suspicious_claims = [
            claim.get("claim", "") 
            for claim in fact_check.get("suspicious_claims", [])
        ]
    
    # Build scam description
    scam_description_parts = [f"Risk Score: {risk_score}%", reason]
    if scam_indicators:
        scam_description_parts.append(f"Indicators: {', '.join(scam_indicators)}")
    if suspicious_claims:
        scam_description_parts.append(f"Red Flags: {', '.join(suspicious_claims[:3])}")  # Top 3
    
    scam_description = " | ".join(scam_description_parts)
    
    task = f"""
You are an automated assistant helping to report a confirmed phone scam to {authority_config['name']}.

GOAL
- Navigate to: {authority_config['url']}
- Fill out the scam reporting form with the details below
- STOP BEFORE FINAL SUBMISSION (do not click "Submit" - we'll review first)
- Summarize what was filled in and confirm the form is ready to submit

SCAM DETAILS
- Scammer Phone Number: {caller_number}
- Victim Phone Number: {user_number}
- Date/Time of Call: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- Scam Type: Phone Fraud / Impersonation Scam
- Description: {scam_description}
- How was contact made: Phone call (inbound to victim)

FORM FILLING INSTRUCTIONS
- Accept cookies if prompted (minimal/necessary only)
- Fill all required fields accurately
- Use the scam details provided above
- For any "victim information" fields, use the victim phone number
- For any "additional details" or "description" fields, include the full scam description
- If asked about monetary loss, indicate "No money lost (prevented by Guardian Agent)"
- CRITICAL: Stop BEFORE clicking any "Submit" or "File Report" button

OUTPUT
- Report what fields were filled
- Confirm form is ready for submission
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
        analysis: Analysis results from assess_scam_probability
        decision: Decision results from agent
        fact_check: Optional fact-check results (for additional context)
        authority: Which authority to report to (default from env or "donotcall")
        headless: Whether to run browser in headless mode
        
    Returns:
        Dict with:
        - status: "success" | "failed" | "disabled"
        - authority: Name of reporting authority
        - message: Summary of what happened
        - form_data: What was filled in the form
        - url: Final page URL
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
            fact_check=fact_check,
            authority_config=authority_config,
        )
        
        # Initialize browser
        browser = Browser(
            config={
                "headless": headless,
                "disable_security": False,  # Keep security enabled
            }
        )
        
        # Initialize LLM (use OpenAI or compatible API)
        api_key = os.getenv("BROWSERUSE_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("BROWSERUSE_KEY or OPENAI_API_KEY not set in .env")
        
        base_url = os.getenv("OPENAI_BASE_URL")
        model = os.getenv("BROWSERUSE_MODEL", "gpt-4o")
        
        if base_url:
            llm = ChatOpenAI(api_key=api_key, base_url=base_url, model=model)
        else:
            llm = ChatOpenAI(api_key=api_key, model=model)
        
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
    authority: Optional[str] = None,
    headless: bool = True,
) -> Dict[str, Any]:
    """
    Synchronous wrapper for report_scam_to_authorities.
    Use this in agent.py nodes (which are synchronous).
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

