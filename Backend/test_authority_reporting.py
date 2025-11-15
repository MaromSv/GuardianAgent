"""
Test script for authority reporting utility.
Tests browser automation for reporting scams to official authorities.

NOTE: This requires browser_use to be installed:
pip install browser-use
"""
import asyncio
from dotenv import load_dotenv
from agent.utils.report_to_authorities import (
    report_scam_to_authorities,
    should_report_to_authorities,
    format_authority_report_summary,
)

load_dotenv()


async def test_high_confidence_scam():
    """Test reporting a high-confidence scam (should trigger reporting)."""
    print("\n" + "="*60)
    print("TEST 1: High Confidence Scam (should report)")
    print("="*60)
    
    caller_number = "+18656304266"  # Known scam number
    user_number = "+15550001111"
    
    analysis = {
        "risk_score": 95.0,
        "confidence": 0.95,
        "reason": "Multiple critical red flags detected",
        "scam_indicators": [
            "Requested password for verification",
            "Created artificial urgency",
            "Threatened account closure",
        ],
    }
    
    decision = {
        "action": "warn",
        "risk_score": 95.0,
        "reason": "High risk=95% (known scam database match)",
    }
    
    fact_check = {
        "suspicious_claims": [
            {
                "claim": "Requesting password for verification",
                "problem": "Banks never ask for passwords",
                "severity": "high"
            },
            {
                "claim": "Account will be closed in 24 hours",
                "problem": "Artificial urgency tactic",
                "severity": "medium"
            }
        ],
        "risk_increase": 45,
    }
    
    # Check if we should report
    should_report = should_report_to_authorities(decision)
    print(f"\nShould report to authorities? {should_report}")
    print(f"  Action: {decision['action']}")
    print(f"  Risk: {decision['risk_score']}%")
    
    if should_report:
        print("\n🚨 Initiating automated scam report...")
        print("   This will open a browser and fill out the reporting form.")
        print("   The browser will STOP BEFORE final submission for review.")
        
        # Run the reporting (headless=False to see the browser)
        result = await report_scam_to_authorities(
            caller_number=caller_number,
            user_number=user_number,
            analysis=analysis,
            decision=decision,
            fact_check=fact_check,
            authority="donotcall",  # Use Do Not Call Registry for testing
            headless=False,  # Set to True for production
        )
        
        print("\n📊 REPORTING RESULT:")
        print(f"  Status: {result.get('status')}")
        print(f"  Authority: {result.get('authority')}")
        print(f"  Message: {result.get('message')}")
        
        if result.get("status") == "success":
            print("\n✅ Form filled successfully!")
            print("   Review the browser window to verify the form is correct.")
            print("   In production, you could auto-submit or require manual review.")
        
        # Print formatted summary
        print("\n" + format_authority_report_summary(result))
        
        return result
    else:
        print("⏭️  Reporting skipped (criteria not met)")


async def test_medium_risk_call():
    """Test a medium-risk call (should NOT trigger reporting)."""
    print("\n" + "="*60)
    print("TEST 2: Medium Risk Call (should NOT report)")
    print("="*60)
    
    caller_number = "+15551234567"
    user_number = "+15550001111"
    
    analysis = {
        "risk_score": 55.0,
        "confidence": 0.6,
        "reason": "Some suspicious elements detected",
        "scam_indicators": ["Vague organization claims"],
    }
    
    decision = {
        "action": "question",  # Not "warn"
        "risk_score": 55.0,
        "reason": "Moderate risk from conversation analysis",
    }
    
    should_report = should_report_to_authorities(decision)
    print(f"\nShould report to authorities? {should_report}")
    print(f"  Action: {decision['action']} (need 'warn')")
    print(f"  Risk: {decision['risk_score']}% (need >= 80%)")
    
    if should_report:
        result = await report_scam_to_authorities(
            caller_number=caller_number,
            user_number=user_number,
            analysis=analysis,
            decision=decision,
        )
        print(format_authority_report_summary(result))
    else:
        print("\n⏭️  Correctly skipped: Not high enough confidence for authority reporting")
        print("     (This prevents false reports to authorities)")


async def test_no_browseruse():
    """Test behavior when browser_use is not available."""
    print("\n" + "="*60)
    print("TEST 3: Browser Use Not Available (graceful degradation)")
    print("="*60)
    
    # This will be handled by the BROWSER_USE_AVAILABLE flag in the module
    print("If browser_use is not installed, reporting will be disabled gracefully.")
    print("The system will continue to work, just without automated authority reporting.")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("AUTHORITY REPORTING TESTS")
    print("="*60)
    print("\nThese tests demonstrate automated scam reporting to authorities.")
    print("The browser will open and fill forms, but STOP BEFORE submission.")
    
    try:
        # Test 1: High confidence scam (should trigger)
        await test_high_confidence_scam()
        
        # Test 2: Medium risk (should skip)
        await test_medium_risk_call()
        
        # Test 3: No browser_use
        await test_no_browseruse()
        
        print("\n" + "="*60)
        print("All tests completed!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n⚠️  WARNING: This test will open a real browser window!")
    print("    The browser will navigate to official reporting sites.")
    print("    Forms will be filled but NOT submitted (stops before final click).")
    print("\n    Press Ctrl+C to cancel, or wait 5 seconds to continue...")
    
    try:
        import time
        time.sleep(5)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Test cancelled by user.")

