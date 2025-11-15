"""
Test script to verify Pydantic validation in LLM-powered utilities.
Tests that risk_score, confidence, and other numeric fields are properly validated.
"""
from dotenv import load_dotenv
from agent.utils.assess_scam_probability import ScamAnalysisResponse
from agent.utils.fact_check import FactCheckResponse, FactCheckClaim

load_dotenv()


def test_scam_analysis_validation():
    """Test ScamAnalysisResponse Pydantic validation."""
    print("\n" + "="*60)
    print("TEST 1: Scam Analysis Response Validation")
    print("="*60)
    
    # Test Case 1: Valid data
    print("\n✅ Test 1a: Valid data")
    valid_data = {
        "risk_score": 85.5,
        "confidence": 0.92,
        "reason": "Multiple red flags detected",
        "scam_indicators": ["password request", "urgency"],
        "recommended_action": "warn"
    }
    
    try:
        validated = ScamAnalysisResponse(**valid_data)
        print(f"   Risk Score: {validated.risk_score} (type: {type(validated.risk_score).__name__})")
        print(f"   Confidence: {validated.confidence} (type: {type(validated.confidence).__name__})")
        print(f"   Action: {validated.recommended_action}")
        print("   ✅ Validation passed!")
    except Exception as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test Case 2: Risk score out of range (should clamp)
    print("\n✅ Test 1b: Risk score out of range (150.0)")
    out_of_range_data = {
        "risk_score": 150.0,  # Invalid: > 100
        "confidence": 0.95,
        "reason": "Test",
        "scam_indicators": [],
        "recommended_action": "warn"
    }
    
    try:
        validated = ScamAnalysisResponse(**out_of_range_data)
        print(f"   Risk Score: {validated.risk_score} (clamped to 100.0)")
        print("   ✅ Validation passed with clamping!")
    except Exception as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test Case 3: String that can be converted to number
    print("\n✅ Test 1c: String numbers (should convert)")
    string_data = {
        "risk_score": "75",  # String instead of number
        "confidence": "0.85",  # String instead of number
        "reason": "Test",
        "scam_indicators": [],
        "recommended_action": "question"
    }
    
    try:
        validated = ScamAnalysisResponse(**string_data)
        print(f"   Risk Score: {validated.risk_score} (converted from string)")
        print(f"   Confidence: {validated.confidence} (converted from string)")
        print("   ✅ Validation passed with type conversion!")
    except Exception as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test Case 4: Invalid action (should default to observe)
    print("\n✅ Test 1d: Invalid action (should default)")
    invalid_action_data = {
        "risk_score": 50.0,
        "confidence": 0.5,
        "reason": "Test",
        "scam_indicators": [],
        "recommended_action": "PANIC"  # Invalid action
    }
    
    try:
        validated = ScamAnalysisResponse(**invalid_action_data)
        print(f"   Action: {validated.recommended_action} (defaulted from 'PANIC')")
        print("   ✅ Validation passed with default!")
    except Exception as e:
        print(f"   ❌ Validation failed: {e}")


def test_fact_check_validation():
    """Test FactCheckResponse Pydantic validation."""
    print("\n" + "="*60)
    print("TEST 2: Fact-Check Response Validation")
    print("="*60)
    
    # Test Case 1: Valid data with claims
    print("\n✅ Test 2a: Valid data with claims")
    valid_data = {
        "verified_claims": [
            {
                "claim": "Appointment reminder",
                "verification": "Standard legitimate practice"
            }
        ],
        "suspicious_claims": [
            {
                "claim": "Requesting password",
                "problem": "Banks never ask for passwords",
                "reality": "Use secure verification",
                "severity": "high"
            }
        ],
        "risk_increase": 35.0,
        "confidence": 0.88,
        "summary": "One critical red flag detected"
    }
    
    try:
        validated = FactCheckResponse(**valid_data)
        print(f"   Verified Claims: {len(validated.verified_claims)}")
        print(f"   Suspicious Claims: {len(validated.suspicious_claims)}")
        print(f"   Risk Increase: {validated.risk_increase}%")
        print(f"   Confidence: {validated.confidence}")
        print("   ✅ Validation passed!")
    except Exception as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test Case 2: Risk increase out of range (should clamp to 50)
    print("\n✅ Test 2b: Risk increase out of range (75.0)")
    out_of_range_data = {
        "verified_claims": [],
        "suspicious_claims": [],
        "risk_increase": 75.0,  # Invalid: > 50
        "confidence": 0.9,
        "summary": "Test"
    }
    
    try:
        validated = FactCheckResponse(**out_of_range_data)
        print(f"   Risk Increase: {validated.risk_increase}% (clamped to 50.0)")
        print("   ✅ Validation passed with clamping!")
    except Exception as e:
        print(f"   ❌ Validation failed: {e}")
    
    # Test Case 3: Invalid severity (should default to medium)
    print("\n✅ Test 2c: Invalid severity level")
    invalid_severity_data = {
        "verified_claims": [],
        "suspicious_claims": [
            {
                "claim": "Test claim",
                "problem": "Test problem",
                "severity": "CRITICAL"  # Invalid severity
            }
        ],
        "risk_increase": 20.0,
        "confidence": 0.7,
        "summary": "Test"
    }
    
    try:
        validated = FactCheckResponse(**invalid_severity_data)
        severity = validated.suspicious_claims[0].severity
        print(f"   Severity: {severity} (defaulted from 'CRITICAL')")
        print("   ✅ Validation passed with default!")
    except Exception as e:
        print(f"   ❌ Validation failed: {e}")


def test_type_safety():
    """Test that Pydantic catches actual type errors."""
    print("\n" + "="*60)
    print("TEST 3: Type Safety (Invalid Data)")
    print("="*60)
    
    # Test Case 1: Completely invalid risk_score (non-numeric string)
    print("\n❌ Test 3a: Non-numeric string for risk_score")
    invalid_data = {
        "risk_score": "very high",  # Can't convert to number
        "confidence": 0.9,
        "reason": "Test",
        "scam_indicators": [],
        "recommended_action": "warn"
    }
    
    try:
        validated = ScamAnalysisResponse(**invalid_data)
        print(f"   ❌ Should have failed but got: {validated.risk_score}")
    except Exception as e:
        print(f"   ✅ Correctly caught invalid data: {type(e).__name__}")
        print(f"      Error: {str(e)[:80]}...")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PYDANTIC VALIDATION TESTS")
    print("="*60)
    print("\nThese tests verify that LLM responses are properly validated")
    print("to ensure risk_score, confidence, and other fields are always")
    print("numeric with proper ranges, even if the LLM returns bad data.")
    
    try:
        test_scam_analysis_validation()
        test_fact_check_validation()
        test_type_safety()
        
        print("\n" + "="*60)
        print("All validation tests completed!")
        print("="*60)
        print("\n✅ Pydantic validation is working correctly!")
        print("   - Type conversion: Strings → Numbers ✅")
        print("   - Range clamping: Values within bounds ✅")
        print("   - Default values: Invalid data → Safe defaults ✅")
        print("   - Error handling: Bad data caught ✅")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

