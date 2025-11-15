# Authority Reporting Integration Guide

## Overview
The authority reporting utility (`agent/utils/report_to_authorities.py`) uses browser automation to automatically report confirmed scam phone numbers to official authorities like the FTC, FBI IC3, or Do Not Call Registry.

## How It Works
- **Triggers ONLY** when action == "warn" AND risk_score >= 80% (high confidence scams)
- Opens a headless browser (or visible for debugging)
- Navigates to official reporting websites
- Fills out scam report forms with call details
- **STOPS BEFORE SUBMISSION** for review (configurable)
- Returns status and form data

## Prerequisites

### 1. Install browser-use
```bash
pip install browser-use
```

### 2. Add to .env
```bash
# Required: API key for browser agent LLM
BROWSERUSE_KEY=your_openai_key_here

# Optional: Which authority to report to (default: donotcall)
SCAM_REPORT_AUTHORITY=donotcall

# Optional: Browser agent model (default: gpt-4o)
BROWSERUSE_MODEL=gpt-4o
```

### 3. Available Authorities
- `donotcall` - National Do Not Call Registry (FTC) - **Default**
- `ftc` - Federal Trade Commission main fraud reporting
- `ic3` - FBI Internet Crime Complaint Center

## Integration Steps

### 1. Add authority_report field to GuardianState

In `agent/agent.py`, update the `GuardianState` TypedDict:

```python
class GuardianState(TypedDict, total=False):
    # ... existing fields ...
    
    # Authority reporting results
    authority_report: Dict[str, Any]  # Results from report_to_authorities
```

### 2. Import the reporting function

At the top of `agent/agent.py`:

```python
from .utils.report_to_authorities import (
    report_scam_to_authorities_sync,
    should_report_to_authorities,
)
```

### 3. Add the authority reporting node

Add this method to the `GuardianAgent` class:

```python
def n_report_to_authorities(self, state: GuardianState) -> GuardianState:
    """
    Report confirmed scam to official authorities using browser automation.
    Only runs when we are 100% confident it's a scam (action == 'warn', risk >= 80%).
    """
    decision = state.get("decision") or {}
    
    # Check if we should report
    if not should_report_to_authorities(decision):
        state["authority_report"] = {
            "status": "skipped",
            "message": "Not high enough confidence to report to authorities"
        }
        _log(state, "authority_report", state["authority_report"])
        return state
    
    # Set current tool for UI
    state["current_tool"] = "authority_reporting"
    state["current_tool_description"] = "Reporting scam to official authorities"
    
    # Report the scam
    result = report_scam_to_authorities_sync(
        caller_number=state.get("caller_number", ""),
        user_number=state.get("user_number", ""),
        analysis=state.get("analysis") or {},
        decision=decision,
        fact_check=state.get("fact_check"),  # Optional, if fact-check is integrated
        headless=True,  # Set to False for debugging
    )
    
    state["authority_report"] = result
    _log(state, "authority_report", result)
    
    return state
```

### 4. Update graph wiring

In the `_setup_graph()` method:

```python
# Add the node
builder.add_node("report_to_authorities", self.n_report_to_authorities)

# Wire it in: process_scam → report_to_authorities → generate_utterance
# (Only runs after we've processed a scam, so we're already at "warn" level)
builder.add_edge("process_scam", "report_to_authorities")
builder.add_edge("report_to_authorities", "generate_utterance")

# Remove old edge: builder.add_edge("process_scam", "generate_utterance")
```

**Updated flow for "warn" action:**
```
decide (action == "warn")
  ↓
process_scam (add to local DB)
  ↓
report_to_authorities (NEW! Report to FTC/FBI/etc.)
  ↓
generate_utterance (Guardian speaks)
  ↓
tts → finalize → END
```

### 5. Optional: Update decision message

You can optionally update the Guardian's message to mention that authorities have been notified:

```python
def n_generate_utterance(self, state: GuardianState) -> GuardianState:
    # ... existing code ...
    
    # Add context about authority reporting
    authority_report = state.get("authority_report")
    if authority_report and authority_report.get("status") == "success":
        # LLM can now use this context to mention: "Authorities have been notified"
        pass
    
    # ... rest of existing code ...
```

## Configuration

### Environment Variables

```bash
# Which authority to report to
SCAM_REPORT_AUTHORITY=donotcall  # Options: donotcall, ftc, ic3

# Browser mode (for debugging)
BROWSERUSE_HEADLESS=true  # Set to false to see browser window

# Browser agent model
BROWSERUSE_MODEL=gpt-4o  # Or gpt-4o-mini for cost savings
```

### In-Code Configuration

You can also specify authority per-call:

```python
result = report_scam_to_authorities_sync(
    # ... other params ...
    authority="ftc",  # Override default
    headless=False,   # Show browser for debugging
)
```

## Testing

### Run Test Suite
```bash
cd Backend
python test_authority_reporting.py
```

**What the test does:**
1. Creates a high-confidence scam scenario (95% risk)
2. Opens a browser window
3. Navigates to Do Not Call Registry
4. Fills out the scam report form
5. **STOPS BEFORE SUBMISSION** for review
6. Shows the filled form in the browser

You can review the form and manually submit if desired.

### Manual Test with Simulation

Run your realistic call simulation, then check the state:

```powershell
# Start backend
python Backend/app.py

# In another terminal, run simulation
.\Backend\simulate_realistic_call.ps1

# Check if authority report was triggered
$response = Invoke-RestMethod -Uri "http://localhost:5000/calls/realistic-test-xxx/state" -Method GET
$response.state.values.authority_report
```

## Frontend Integration

### Update TypeScript Types

In `Frontend/src/types/guardian.ts`:

```typescript
export interface AuthorityReport {
  status: "success" | "failed" | "skipped" | "disabled";
  authority?: string;
  authority_url?: string;
  message: string;
  form_data?: {
    scammer_number: string;
    victim_number: string;
    risk_score: number;
    timestamp: string;
  };
  error?: string;
}

export interface GuardianAgentState {
  // ... existing fields ...
  authority_report?: AuthorityReport;
}
```

### Display in UI

Create a new component `AuthorityReportStatus.tsx`:

```tsx
import { CheckCircle, AlertTriangle, Info } from "lucide-react";

interface AuthorityReportStatusProps {
  report: AuthorityReport | null;
}

export function AuthorityReportStatus({ report }: AuthorityReportStatusProps) {
  if (!report || report.status === "skipped") return null;
  
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center gap-2 mb-2">
        {report.status === "success" ? (
          <CheckCircle className="h-5 w-5 text-green-600" />
        ) : (
          <AlertTriangle className="h-5 w-5 text-yellow-600" />
        )}
        <h3 className="text-base font-medium">Authority Report</h3>
      </div>
      
      <p className="text-sm text-muted-foreground mb-2">
        {report.message}
      </p>
      
      {report.authority && (
        <p className="text-xs text-muted-foreground">
          Reported to: {report.authority}
        </p>
      )}
    </div>
  );
}
```

Add to `CallMonitor.tsx`:
```tsx
<AuthorityReportStatus report={state?.authority_report} />
```

## Security & Privacy

### What Gets Reported
- Scammer's phone number
- Date/time of call
- Risk score and scam indicators
- Description of scam tactics used

### What Does NOT Get Reported
- Actual conversation transcript (for privacy)
- Victim's personal details beyond phone number
- Guardian's analysis details (only summary)

### Submission Control
By default, the system **stops before final submission** so you can:
1. Review the filled form
2. Verify accuracy
3. Manually click "Submit" if desired

To enable auto-submission (not recommended for initial deployment):
```python
# In the task prompt, remove the "STOP BEFORE SUBMISSION" instruction
# This requires careful testing and legal review
```

## Legal Considerations

⚠️ **Important:**
- Automated reporting to government agencies should be reviewed by legal counsel
- Ensure compliance with local laws regarding automated form submission
- Consider liability for false reports (hence the high confidence threshold)
- The default "stop before submission" mode allows human review

## Troubleshooting

### Browser doesn't open
- Check `BROWSERUSE_KEY` is set in `.env`
- Try `headless=False` to see browser window
- Ensure browser-use is installed: `pip install browser-use`

### Form filling fails
- Check the authority website hasn't changed its layout
- Try a different authority: `authority="ftc"` instead of `"donotcall"`
- Review browser console logs for errors

### "browser_use not installed" warning
- Run: `pip install browser-use`
- System will continue working, just without automated reporting

## Example Output

### Successful Report
```json
{
  "status": "success",
  "authority": "National Do Not Call Registry",
  "authority_url": "https://complaints.donotcall.gov/...",
  "message": "Scam report form filled and ready for submission",
  "form_data": {
    "scammer_number": "+18656304266",
    "victim_number": "+15550001111",
    "risk_score": 95.0,
    "timestamp": "2025-11-15T14:30:00"
  }
}
```

### Skipped (Low Risk)
```json
{
  "status": "skipped",
  "message": "Not reporting: action=question, risk=55% (need warn + 80%+)",
  "authority": null
}
```

## Notes
- Authority reporting runs **after** local database update (process_scam)
- Only triggers for action == "warn" AND risk >= 80%
- Uses browser automation to fill official government forms
- Defaults to stopping before submission for review
- Gracefully degrades if browser-use not installed
- Configurable authority (FTC, FBI IC3, Do Not Call Registry)

## Ready to Deploy!

Once integrated, Guardian will not only:
1. ✅ Detect scams in real-time
2. ✅ Intervene to protect the user
3. ✅ Add scammers to local database
4. ✅ **Report to official authorities automatically** ← NEW!

This creates a feedback loop that helps authorities track and prosecute scammers! 🚨

