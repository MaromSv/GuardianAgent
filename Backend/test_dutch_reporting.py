"""
Test script for Dutch Fraud Help Desk scam reporting.
This runs the browser in VISIBLE mode so you can watch what happens.

Requirements:
    pip install browser-use langchain-openai playwright
    playwright install chromium
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.utils.report_to_authorities import report_scam_to_authorities

# Load environment variables
load_dotenv()


async def test_dutch_reporting():
    """
    Test reporting a scam to FTC (US).
    Browser will be VISIBLE so you can watch it work.
    """
    print("=" * 60)
    print("Testing FTC (US) Scam Reporting")
    print("=" * 60)
    print()
    print("ℹ️  This will open a browser window so you can watch!")
    print("ℹ️  The browser will NOT submit the form (stops before submission)")
    print()
    
    # Test data: High-risk scam call (US)
    test_caller_number = "5002311231"  # Fake 10-digit US number
    test_user_number = "5550001111"    # Fake 10-digit victim number (US)
    
    test_reputation_check = {
        "phone_number": "5002311231",
        "risk_score": 95.0,
        "known_scam": True,
        "source": "local_scam_db",
        "scam_type": "Banking Fraud - Impersonates bank representative",
        "database_match": True,
    }
    
    test_transcript = [
        {"speaker": "caller", "text": "Hello, this is calling from Wells Fargo bank security department."},
        {"speaker": "user", "text": "Yes? Is there a problem?"},
        {"speaker": "caller", "text": "We detected unusual activity on your account. Someone tried to transfer $5,000."},
        {"speaker": "user", "text": "Oh no! What should I do?"},
        {"speaker": "caller", "text": "I need to verify your identity. Can you provide your account number and password?"},
        {"speaker": "guardian", "text": "Excuse me, could you provide your employee ID and a callback number we can verify?"},
    ]
    
    test_analysis = {
        "risk_score": 95.0,
        "confidence": 0.95,
        "reason": "Caller impersonated a bank representative and requested account credentials",
        "scam_indicators": [
            "Urgency tactics (immediate action required)",
            "Requested sensitive information (account password)",
            "Caller ID spoofing detected",
            "No legitimate callback number provided",
        ],
        "recommended_action": "warn",
        "model": "gpt-4o-mini",
    }
    
    test_decision = {
        "action": "warn",
        "reason": "High risk=95% from conversation analysis",
        "risk_score": 95.0,
    }
    
    test_fact_check = {
        "suspicious_claims": [
            {
                "claim": "Your account has been compromised",
                "problem": "No verification provided",
                "severity": "high",
            },
            {
                "claim": "You must act within 30 minutes",
                "problem": "Urgency tactic typical of scams",
                "severity": "high",
            },
        ],
        "risk_increase": 15.0,
        "confidence": 0.9,
        "summary": "Multiple red flags detected in caller's claims",
    }
    
    print("📋 Test Scam Details:")
    print(f"   Scammer Number: {test_caller_number}")
    print(f"   Victim Number: {test_user_number}")
    print(f"   Risk Score: {test_analysis['risk_score']}%")
    print(f"   Action: {test_decision['action']}")
    print()
    print("🚀 Starting browser automation...")
    print("   (This may take 30-60 seconds)")
    print()
    
    try:
        result = await report_scam_to_authorities(
            caller_number=test_caller_number,
            user_number=test_user_number,
            analysis=test_analysis,
            decision=test_decision,
            fact_check=test_fact_check,
            reputation_check=test_reputation_check,  # From phone check node
            transcript=test_transcript,              # Call conversation
            authority="ftc",                         # US Federal Trade Commission
            headless=False,                          # Browser visibility is handled by browser-use
        )
        
        print()
        print("=" * 60)
        print("📊 RESULT")
        print("=" * 60)
        print()
        print(f"Status: {result.get('status')}")
        print(f"Authority: {result.get('authority')}")
        print(f"Message: {result.get('message')}")
        print()
        
        if result.get("form_data"):
            print("Form Data Filled:")
            for key, value in result["form_data"].items():
                print(f"  - {key}: {value}")
        
        if result.get("error"):
            print(f"\n❌ Error: {result['error']}")
        
        print()
        print("=" * 60)
        
        return result
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run the test."""
    print()
    print("🇺🇸 FTC Scam Reporting Test")
    print()
    
    # Set browser to visible mode (not headless)
    import os
    os.environ["HEADLESS"] = "false"  # Make browser visible
    print("🌐 Browser will open in VISIBLE mode")
    print()
    
    # Check if browser-use is installed
    try:
        import browser_use
        print("✅ browser-use is installed")
    except ImportError:
        print("❌ browser-use not installed!")
        print()
        print("To install, run:")
        print("   pip install browser-use langchain-openai playwright")
        print("   playwright install chromium")
        print()
        return
    
    # Check if API key is set
    import os
    api_key = os.getenv("BROWSERUSE_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ API key not found!")
        print()
        print("ChatBrowserUse looks for these environment variables:")
        print("   BROWSERUSE_KEY (checked first)")
        print("   OPENAI_API_KEY (fallback)")
        print()
        print("Add to your .env file:")
        print("   BROWSERUSE_KEY=your_key_here")
        print()
        return
    
    # Show which key is being used
    if os.getenv("BROWSERUSE_KEY"):
        print("✅ Using BROWSERUSE_KEY from .env")
    else:
        print("✅ Using OPENAI_API_KEY from .env")
    
    print("✅ Environment configured")
    print()
    
    # Run the async test
    result = asyncio.run(test_dutch_reporting())
    
    if result:
        print()
        print("✅ Test completed!")
        print()
        print("💡 What happened:")
        print("   1. Browser opened and navigated to reportfraud.ftc.gov")
        print("   2. AI agent looked for the fraud reporting form")
        print("   3. Form fields were filled with scam details")
        print("   4. Agent STOPPED before clicking Submit (as instructed)")
        print()
        print("💡 Next steps:")
        print("   - Review the form data above")
        print("   - If satisfied, the form would be ready to submit")
        print("   - In production, you could manually review before submission")
    else:
        print()
        print("❌ Test did not complete successfully")


if __name__ == "__main__":
    main()

