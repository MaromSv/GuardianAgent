import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback

from browser_use import Agent, Browser, ChatBrowserUse


def _build_reporting_task(
    caller_number: str,
    user_number: str,
    transcript: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Build the task prompt for the browser agent.

    Very simple API:
    - takes the scammer's number
    - your own number
    - and (optionally) the raw transcript
    """
    # Turn transcript into a plain text conversation block
    transcript_lines: List[str] = []
    if transcript:
        for entry in transcript:
            speaker = (
                entry.get("speaker")
                or entry.get("role")
                or "unknown"
            )
            text = (entry.get("text") or "").strip()
            if not text:
                continue
            transcript_lines.append(f"{speaker}: {text}")

    if transcript_lines:
        transcript_text = "\n".join(transcript_lines)
    else:
        transcript_text = (
            "No detailed transcript is available. Assume this was a typical phone scam "
            "where the caller pretended to be from a legitimate organization and tried "
            "to obtain personal or financial information over the phone."
        )

    task = f"""
You are an automated assistant helping to report a phone scam to the FTC Do Not Call Registry.

GOAL
- Navigate directly to the complaint form: https://complaints.donotcall.gov/complaint/complaintcheck.aspx
- Fill out the complaint form with the scam details below
- IMPORTANT: Fill all required fields but DO NOT CLICK the "Submit" button!
- Once you reach a review/confirmation page, STOP immediately

STEP-BY-STEP INSTRUCTIONS
1. Navigate to: https://complaints.donotcall.gov/complaint/complaintcheck.aspx
2. Look for fields asking about:
   - Phone number that called you: Use {caller_number}
   - Your phone number: Use {user_number}
   - Date/time of call: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
   - Description/complaint details: Write a short summary (2-4 sentences) based on the transcript below
3. Fill all required fields
4. When you see a "Submit" or "File Complaint" button, STOP - do NOT click it
5. Report back what fields you filled

SCAM DETAILS
- Scammer Phone Number: {caller_number}
- Your Phone Number: {user_number}
- Date/Time of Call: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

CONVERSATION TRANSCRIPT (use this to write the description):
{transcript_text}

DESCRIPTION GUIDELINES
- Write 2-4 sentences in plain, natural language
- Describe what the caller said and what they tried to do
- Example: "The caller claimed to be from Microsoft and said my license was expiring. They asked for my bank account information to process a renewal payment."
- Base it on the transcript - don't make up details

SAFETY RULES
- DO fill out all form fields
- DO NOT click "Submit"!
- STOP when you reach any review/confirmation page

OUTPUT
- List which fields you successfully filled
- Confirm you did NOT submit the form
- Provide the current page URL
"""
    return task


async def report_scam_to_authorities(
    caller_number: str,
    user_number: str,
    transcript: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Very simple browser-use wrapper to prepare a scam report form.

    Args:
        caller_number: The scammer's phone number (the one being reported).
        user_number:   Your own number / the victim's number.
        transcript:    Optional list of {speaker, text} dicts for the conversation.

    Environment:
        BROWSERUSE_KEY or OPENAI_API_KEY: API key for browser_use / LLM.

    Returns:
        Dict with:
        - status: "success" | "failed"
        - authority: Name of reporting authority
        - authority_url: URL used for reporting
        - message: Summary of what happened
        - form_data: Basic metadata (numbers, timestamp)
        - browser_result: Raw result object from browser_use
        - error: Error message if failed
    """
    try:
        authority_name = "FTC Do Not Call Registry"
        authority_url = "https://complaints.donotcall.gov/complaint/complaintcheck.aspx"

        print(f"🚨 Preparing scam report via browser automation...")
        print(f"   Scammer: {caller_number}")
        print(f"   Victim:  {user_number}")

        # Build task for browser agent (description is derived from transcript)
        task = _build_reporting_task(
            caller_number=caller_number,
            user_number=user_number,
            transcript=transcript,
        )

        # Initialize browser (HEADLESS is controlled via environment if you want)
        browser = Browser()

        # Initialize LLM (browser-use handles API key from environment automatically)
        llm = ChatBrowserUse()

        # Create and run agent
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
        )

        print("🤖 Browser agent starting...")
        # Add timeout to prevent hanging (5 minutes max)
        try:
            history = await asyncio.wait_for(agent.run(), timeout=300.0)
        except asyncio.TimeoutError:
            raise Exception("Browser automation timed out after 5 minutes")

        final_result = history[-1] if history else {}

        print(f"✅ Scam report form prepared for {authority_name}")

        return {
            "status": "success",
            "authority": authority_name,
            "authority_url": authority_url,
            "message": f"Scam report form filled and ready for manual review at {authority_name}",
            "form_data": {
                "scammer_number": caller_number,
                "victim_number": user_number,
                "timestamp": datetime.now().isoformat(),
            },
            "browser_result": final_result,
        }

    except Exception as e:
        error_msg = f"Error preparing scam report via browser automation: {e}"
        print(f"❌ {error_msg}")
        traceback.print_exc()

        return {
            "status": "failed",
            "authority": "FTC Do Not Call Registry",
            "authority_url": "https://complaints.donotcall.gov/complaint/complaintcheck.aspx",
            "message": error_msg,
            "error": str(e),
        }


def report_scam_to_authorities_sync(
    caller_number: str,
    user_number: str,
    transcript: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Synchronous wrapper for report_scam_to_authorities.
    Simple, node-friendly API: just pass the numbers and (optionally) the transcript.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            report_scam_to_authorities(
                caller_number=caller_number,
                user_number=user_number,
                transcript=transcript,
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


# Helper function to format reporting summary for logs / UI
def format_authority_report_summary(report_result: Dict[str, Any]) -> str:
    """
    Format authority reporting results into a readable summary.
    """
    status = report_result.get("status", "unknown")
    authority = report_result.get("authority", "Unknown Authority")
    message = report_result.get("message", "")

    if status == "success":
        return f"✅ Scam report prepared for {authority}. {message}"
    else:
        error = report_result.get("error", "Unknown error")
        return f"❌ Failed to prepare scam report for {authority}: {error}"

