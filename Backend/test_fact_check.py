"""
Test script for the fact-checking utility.
Tests both LLM-based and fallback fact-checking.
"""
from dotenv import load_dotenv
from agent.utils.fact_check import fact_check_claims, format_fact_check_report

load_dotenv()


def test_case(name: str, transcript: list):
    """Run a test case and print results."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    
    # Show conversation
    print("\nConversation:")
    for entry in transcript:
        speaker = entry["speaker"].upper()
        text = entry["text"]
        print(f"  {speaker}: {text}")
    
    # Run fact-check
    print("\n🔍 Running fact-check...")
    results = fact_check_claims(transcript)
    
    # Print formatted report
    print("\n" + format_fact_check_report(results))
    print(f"\nModel used: {results.get('model', 'unknown')}")
    print(f"Confidence: {results.get('confidence', 0):.0%}")


# Test Case 1: Classic bank scam with password request
test_case(
    "Classic Bank Scam (Password Request)",
    [
        {"speaker": "caller", "text": "Hello, this is John from Wells Fargo security department."},
        {"speaker": "user", "text": "Oh, hi. What's this about?"},
        {"speaker": "caller", "text": "We detected suspicious activity on your account ending in 4523."},
        {"speaker": "user", "text": "Really? What kind of activity?"},
        {"speaker": "caller", "text": "Someone tried to transfer $5,000. To verify your identity, I need your password and account number."},
        {"speaker": "user", "text": "Okay, my password is..."},
    ]
)

# Test Case 2: IRS scam with arrest threat
test_case(
    "IRS Scam (Arrest Threat)",
    [
        {"speaker": "caller", "text": "This is Officer Johnson from the IRS. You have unpaid taxes from 2019."},
        {"speaker": "user", "text": "I don't remember owing anything."},
        {"speaker": "caller", "text": "If you don't pay immediately, a warrant will be issued for your arrest within 24 hours."},
        {"speaker": "user", "text": "That's scary! What do I need to do?"},
        {"speaker": "caller", "text": "You need to wire $2,500 to our processing center right now, or the police will come to your home."},
    ]
)

# Test Case 3: Gift card scam
test_case(
    "Tech Support Scam (Gift Cards)",
    [
        {"speaker": "caller", "text": "This is Microsoft technical support. Your computer has been infected with a virus."},
        {"speaker": "user", "text": "Oh no! How do you know?"},
        {"speaker": "caller", "text": "We monitor all Windows computers. To remove the virus, you need to pay $300 in iTunes gift cards."},
        {"speaker": "user", "text": "Why gift cards?"},
        {"speaker": "caller", "text": "That's our standard payment method. Go buy the cards and read me the codes immediately."},
    ]
)

# Test Case 4: Legitimate conversation
test_case(
    "Legitimate Call (No Red Flags)",
    [
        {"speaker": "caller", "text": "Hi, this is Sarah from your doctor's office."},
        {"speaker": "user", "text": "Hello!"},
        {"speaker": "caller", "text": "I'm calling to remind you about your appointment next Tuesday at 2 PM."},
        {"speaker": "user", "text": "Thanks for the reminder!"},
        {"speaker": "caller", "text": "No problem! If you need to reschedule, just call us back at the number on your appointment card."},
    ]
)

# Test Case 5: Account frozen scam (high urgency)
test_case(
    "Frozen Account Scam (Urgency Tactic)",
    [
        {"speaker": "caller", "text": "This is Bank of America fraud prevention. Your account has been frozen."},
        {"speaker": "user", "text": "Why was it frozen?"},
        {"speaker": "caller", "text": "Suspicious transactions from Nigeria. You must provide your SSN and routing number immediately or the account will be closed permanently."},
        {"speaker": "user", "text": "Can I call you back?"},
        {"speaker": "caller", "text": "No, don't hang up! The system will lock you out if you disconnect."},
    ]
)

print("\n" + "="*60)
print("All tests completed!")
print("="*60)

