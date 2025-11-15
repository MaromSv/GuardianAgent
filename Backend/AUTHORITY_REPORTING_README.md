# Authority Reporting System - Ready for Integration

## ✅ What's Complete

### Backend
- **`agent/utils/report_to_authorities.py`** - Browser automation for reporting scams
  - Connects to official government sites (FTC, FBI IC3, Do Not Call Registry)
  - Fills out scam report forms automatically
  - Stops before submission for review (configurable)
  - Supports both async and sync operation (for agent.py nodes)
  
- **`test_authority_reporting.py`** - Test suite with browser automation
  - High confidence scam (should trigger)
  - Medium risk call (should skip)
  - Graceful degradation tests
  
- **`AUTHORITY_REPORTING_INTEGRATION.md`** - Complete integration guide
  - Step-by-step instructions for agent.py
  - Graph wiring details
  - Configuration options
  - Security & legal considerations

### Frontend
- **`src/types/guardian.ts`** - Updated TypeScript types
  - `AuthorityReport` interface
  - Added to `GuardianAgentState`
  
- **`src/components/AuthorityReportStatus.tsx`** - Display component
  - Shows successful reports (✅ green)
  - Shows failed reports (⚠️ red)
  - Displays authority name, timestamp, form data
  - Links to reporting site
  
- **`src/components/ConversationView.tsx`** - Updated status bar
  - Added "Reporting to authorities" status

## 🎯 How It Works

### Trigger Conditions
**Reports ONLY when:**
- ✅ Decision action == `"warn"` (highest severity)
- ✅ Risk score >= 80% (very high confidence)

This prevents false reports to authorities!

### What Gets Reported
- **Scammer's phone number** - The malicious caller
- **Date/Time** - When the scam call occurred
- **Risk score** - How confident we are (80-100%)
- **Scam description** - Summary of tactics used:
  - "Requested password for verification"
  - "Created artificial urgency"
  - "Threatened account closure"
  - "Known scam database match"

### What Does NOT Get Reported
- ❌ Conversation transcript (privacy)
- ❌ Victim's personal details (beyond phone number)
- ❌ Guardian's internal analysis details

### Available Authorities

#### 1. **National Do Not Call Registry** (Default)
- **Website:** https://complaints.donotcall.gov/
- **Run by:** Federal Trade Commission (FTC)
- **Best for:** Unwanted/scam phone calls
- **Config:** `SCAM_REPORT_AUTHORITY=donotcall`

#### 2. **Federal Trade Commission (FTC)**
- **Website:** https://reportfraud.ftc.gov/
- **Run by:** FTC Consumer Protection
- **Best for:** General fraud/scams
- **Config:** `SCAM_REPORT_AUTHORITY=ftc`

#### 3. **FBI Internet Crime Complaint Center (IC3)**
- **Website:** https://www.ic3.gov/
- **Run by:** FBI
- **Best for:** Serious fraud for federal investigation
- **Config:** `SCAM_REPORT_AUTHORITY=ic3`

## 🛠️ Installation

### 1. Install browser-use
```bash
pip install browser-use
```

### 2. Update requirements.txt
```bash
echo "browser-use" >> requirements.txt
```

### 3. Configure .env
```bash
# Required: API key for browser agent
BROWSERUSE_KEY=your_openai_key_here

# Optional: Which authority (default: donotcall)
SCAM_REPORT_AUTHORITY=donotcall

# Optional: Model for browser agent (default: gpt-4o)
BROWSERUSE_MODEL=gpt-4o

# Optional: Headless mode (default: true)
BROWSERUSE_HEADLESS=true
```

## 🧪 Testing

### Run Test Suite
```bash
cd Backend
python test_authority_reporting.py
```

**What happens:**
1. Creates a high-confidence scam scenario (95% risk, "warn" action)
2. Opens a browser window (visible, not headless)
3. Navigates to Do Not Call Registry
4. Fills out the scam report form
5. **STOPS before submission** - you can review the form
6. Shows filled form in browser for manual verification

**Expected output:**
```
TEST 1: High Confidence Scam (should report)
============================================================
Should report to authorities? True
  Action: warn
  Risk: 95.0%

🚨 Reporting scam to National Do Not Call Registry...
   Scammer: +18656304266
   Risk: 95%

🤖 Browser agent starting...
✅ Scam report prepared for National Do Not Call Registry

📊 REPORTING RESULT:
  Status: success
  Authority: National Do Not Call Registry
  Message: Scam report form filled and ready for submission

✅ Form filled successfully!
   Review the browser window to verify the form is correct.
```

### What You'll See
- **Browser window opens** showing Do Not Call Registry
- **Form fields fill automatically:**
  - Phone number: The scammer's number
  - Date/Time: Current timestamp
  - Description: Risk score and scam indicators
  - Type: Phone scam/fraud
- **Browser stops at review page** - does NOT auto-submit
- You can **manually click "Submit"** if everything looks correct

## 🔗 Integration into agent.py

### Quick Integration Checklist
When you're ready to integrate (after others finish with agent.py):

- [ ] Add `authority_report: Dict[str, Any]` to `GuardianState`
- [ ] Import: `from .utils.report_to_authorities import report_scam_to_authorities_sync, should_report_to_authorities`
- [ ] Create `n_report_to_authorities()` node
- [ ] Add node to graph: `builder.add_node("report_to_authorities", self.n_report_to_authorities)`
- [ ] Wire: `process_scam → report_to_authorities → generate_utterance`

**See `AUTHORITY_REPORTING_INTEGRATION.md` for complete code snippets!**

### Where It Fits in the Pipeline

**Current flow (warn action):**
```
decide (action == "warn")
  ↓
process_scam (add to local DB)
  ↓
generate_utterance (Guardian speaks)
  ↓
tts → finalize
```

**New flow with authority reporting:**
```
decide (action == "warn")
  ↓
process_scam (add to local DB)
  ↓
report_to_authorities (NEW! Report to FTC/FBI/etc.) ← ADD HERE
  ↓
generate_utterance (Guardian speaks - can mention "authorities notified")
  ↓
tts → finalize
```

## 🎨 Frontend Display

Once integrated, add to `CallMonitor.tsx`:

```tsx
import { AuthorityReportStatus } from "@/components/AuthorityReportStatus";

// In the right sidebar, after RiskSummary:
<AuthorityReportStatus state={state} />
```

**What users will see:**

### Successful Report
```
┌─────────────────────────────────────────┐
│ ✅ Authority Report                     │
│                                         │
│ Scam report form filled and ready      │
│ for submission to National Do Not      │
│ Call Registry                          │
│                                         │
│ ℹ️ Reported to: National Do Not Call   │
│    Registry                            │
│                                         │
│ Report Details:                        │
│ • Scammer Number: +18656304266         │
│ • Risk Score: 95%                      │
│ • Timestamp: 11/15/2025, 2:30 PM      │
│                                         │
│ View reporting site ↗                  │
│                                         │
│ Scam successfully reported   [SUCCESS] │
└─────────────────────────────────────────┘
```

### No Report (Low Risk)
```
(Component doesn't render if risk < 80% or action != "warn")
```

## 🔒 Security & Legal Considerations

### Submission Control
By default, the system **stops before final submission**:
- ✅ Forms are filled but NOT submitted
- ✅ Human can review before submitting
- ✅ Prevents accidental false reports
- ✅ Allows legal review

### To Enable Auto-Submission
⚠️ **Not recommended without legal review:**
```python
# In report_to_authorities.py, modify the task prompt:
# Remove "STOP BEFORE FINAL SUBMISSION" instruction
# Add "Click Submit button after filling form"
```

### Legal Notes
- Automated government form submission may require legal review
- High confidence threshold (80%+) reduces false report risk
- Default "stop before submit" allows human oversight
- Consider consulting with legal counsel before enabling auto-submission

## 🚨 Example Scenarios

### Scenario 1: Classic Bank Scam (Will Report)
```python
Decision: {
  "action": "warn",
  "risk_score": 95.0,
  "reason": "Known scam number + password request"
}

Authority Report: {
  "status": "success",
  "authority": "National Do Not Call Registry",
  "message": "Form filled and ready for submission"
}
```

### Scenario 2: Suspicious Call (Will NOT Report)
```python
Decision: {
  "action": "question",  # Not "warn"
  "risk_score": 55.0,
  "reason": "Some suspicious elements"
}

Authority Report: {
  "status": "skipped",
  "message": "Not high enough confidence to report"
}
```

### Scenario 3: Legitimate Call (Will NOT Report)
```python
Decision: {
  "action": "observe",
  "risk_score": 5.0,
  "reason": "No risk detected"
}

Authority Report: None (not even checked)
```

## 🔍 Debugging

### Enable Visible Browser
```bash
# In .env
BROWSERUSE_HEADLESS=false
```
Or in code:
```python
report_scam_to_authorities_sync(
    # ... params ...
    headless=False,  # Show browser window
)
```

### Common Issues

**"browser_use not installed"**
- Fix: `pip install browser-use`
- System continues working without authority reporting

**"BROWSERUSE_KEY not set"**
- Fix: Add to `.env`: `BROWSERUSE_KEY=your_openai_key`
- Can use same key as `OPENAI_API_KEY`

**Form filling fails**
- Website layout may have changed
- Try different authority: `authority="ftc"` instead of `"donotcall"`
- Check browser console for errors

**Browser doesn't open**
- Check headless setting: `BROWSERUSE_HEADLESS=false`
- Verify browser-use installation

## 💡 Why This Matters

### Before Authority Reporting:
1. Guardian detects scam ✅
2. Guardian intervenes ✅
3. Guardian adds to local DB ✅
4. ❌ Authorities never notified
5. ❌ Scammer continues calling others

### After Authority Reporting:
1. Guardian detects scam ✅
2. Guardian intervenes ✅
3. Guardian adds to local DB ✅
4. **Guardian reports to FTC/FBI/etc.** ✅ **NEW!**
5. **Authorities track and prosecute** ✅ **NEW!**
6. **Scammer's number gets flagged nationally** ✅ **NEW!**

**Creates a feedback loop that protects everyone, not just your users!** 🚨

## 📊 Statistics

Once deployed, you can track:
- Number of scams reported to authorities
- Which authorities received reports
- Success rate of automated reporting
- Time saved vs. manual reporting

Example stats query:
```python
# Count successful authority reports
successful_reports = sum(
    1 for activity in state["activity"]
    if activity.get("stage") == "authority_report"
    and activity.get("data", {}).get("status") == "success"
)
```

## 🚀 Ready to Deploy!

Once integrated, Guardian becomes a **proactive scam-fighting system**:

1. **Detects** scams using AI + phone reputation + fact-checking
2. **Protects** users by intervening in real-time
3. **Records** scammers in local database
4. **Reports** to official authorities for prosecution
5. **Prevents** future victims by contributing to national databases

**This is exactly what you envisioned with `browser_agent.py`!** 🎯

---

## Quick Start (Once Ready)

```bash
# 1. Install dependencies
pip install browser-use

# 2. Configure
echo "BROWSERUSE_KEY=sk-..." >> .env
echo "SCAM_REPORT_AUTHORITY=donotcall" >> .env

# 3. Test
python Backend/test_authority_reporting.py

# 4. Integrate into agent.py (see AUTHORITY_REPORTING_INTEGRATION.md)

# 5. Deploy and watch Guardian protect users + report scammers! 🚨
```

