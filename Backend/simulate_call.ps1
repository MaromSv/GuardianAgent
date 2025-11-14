# Simulate a call conversation for testing
# Usage: .\simulate_call.ps1 -CallSid "test-call-123"

param(
    [string]$CallSid = "test-call-123",
    [string]$BackendUrl = "http://localhost:5000"
)

$userNumber = "+15550001111"
$callerNumber = "+15656304266"  # Known scam number from database (Wells Fargo impersonation)

# Function to check and display current tool use
function Show-ToolUse {
    param([string]$BackendUrl, [string]$CallSid)
    
    try {
        $stateResponse = Invoke-RestMethod -Uri "$BackendUrl/calls/$CallSid/state" -Method GET -ErrorAction SilentlyContinue
        $currentTool = $stateResponse.state.values.current_tool
        $toolDescription = $stateResponse.state.values.current_tool_description
        
        if ($currentTool -and $currentTool -ne "") {
            # Map tool names to display names
            $toolNames = @{
                "phone_reputation_check" = "[PHONE] Phone Reputation Check"
                "transcript_analysis" = "[BRAIN] Transcript Analysis"
                "web_search" = "[SEARCH] Web Search"
                "decision_making" = "[SHIELD] Decision Making"
                "speech_generation" = "[SPEECH] Speech Generation"
            }
            
            $displayName = $toolNames[$currentTool]
            if (-not $displayName) {
                $displayName = $currentTool
            }
            
            Write-Host "  [TOOL] Tool Active: $displayName" -ForegroundColor Cyan
            if ($toolDescription) {
                Write-Host "        -> $toolDescription" -ForegroundColor Gray
            }
            return $true
        }
        return $false
    }
    catch {
        return $false
    }
}

Write-Host "=== Simulating Call: $CallSid ===" -ForegroundColor Cyan
Write-Host "Backend URL: $BackendUrl`n" -ForegroundColor Gray

# Conversation script - simulating a scam call
$conversation = @(
    @{ speaker = "caller"; text = "Hello, this is John from your bank's security department." },
    @{ speaker = "caller"; text = "We detected unusual activity on your account." },
    @{ speaker = "user"; text = "Oh no, what kind of activity?" },
    @{ speaker = "caller"; text = "Someone tried to transfer $5,000 from your account." },
    @{ speaker = "caller"; text = "To verify your identity, I need your account number and password." },
    @{ speaker = "user"; text = "Really? That's concerning." },
    @{ speaker = "caller"; text = "Yes, and I also need your social security number to secure your account." },
    @{ speaker = "caller"; text = "This is urgent - we need to act quickly to protect your funds." }
)

$chunkNumber = 1
foreach ($chunk in $conversation) {
    Write-Host "[$chunkNumber] Sending: $($chunk.speaker) - '$($chunk.text)'" -ForegroundColor Yellow
    
    $body = @{
        text = $chunk.text
        speaker = $chunk.speaker
        user_number = $userNumber
        caller_number = $callerNumber
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$BackendUrl/calls/$CallSid/transcript" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body
        
        # Small delay to let backend process
        Start-Sleep -Milliseconds 300
        
        # Check for active tool use
        $toolActive = Show-ToolUse -BackendUrl $BackendUrl -CallSid $CallSid
        
        # Show decision if available
        if ($response.decision) {
            $action = $response.decision.action
            $risk = $response.decision.risk_score
            Write-Host "  → Decision: $action (Risk: $risk)" -ForegroundColor $(if ($risk -gt 70) { "Red" } elseif ($risk -gt 40) { "Yellow" } else { "Green" })
        }
        
        # Show guardian utterance if available
        if ($response.audio_url -and $response.audio_url -ne "") {
            Write-Host "  → Guardian intervened!" -ForegroundColor Magenta
        }
        
        # Show activity log entries with tool info
        if ($response.activity) {
            $recentActivity = $response.activity[-1]  # Get last activity entry
            if ($recentActivity.tool) {
                $toolNames = @{
                    "phone_reputation_check" = "[PHONE] Phone Check"
                    "transcript_analysis" = "[BRAIN] Analysis"
                    "web_search" = "[SEARCH] Web Search"
                    "decision_making" = "[SHIELD] Decision"
                    "speech_generation" = "[SPEECH] Speech"
                }
                $toolDisplay = $toolNames[$recentActivity.tool]
                if (-not $toolDisplay) {
                    $toolDisplay = $recentActivity.tool
                }
                Write-Host "  [LOG] Activity: $($recentActivity.stage) [$toolDisplay]" -ForegroundColor DarkGray
            }
        }
        
        # Realistic delay between messages (2-5 seconds)
        # Simulates natural conversation pauses
        $delay = Get-Random -Minimum 2000 -Maximum 5000
        Start-Sleep -Milliseconds $delay
        $chunkNumber++
    }
    catch {
        Write-Host "  [ERROR] $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "=== Call Simulation Complete ===" -ForegroundColor Green

# Final state check
Write-Host "`n=== Final State Summary ===" -ForegroundColor Cyan
try {
    $finalState = Invoke-RestMethod -Uri "$BackendUrl/calls/$CallSid/state" -Method GET
    $state = $finalState.state.values
    
    Write-Host "Call SID: $($state.call_sid)" -ForegroundColor Gray
    Write-Host "Transcript entries: $($state.transcript.Count)" -ForegroundColor Gray
    Write-Host "Activity log entries: $($state.activity.Count)" -ForegroundColor Gray
    
    if ($state.decision) {
        Write-Host "Final Decision: $($state.decision.action) (Risk: $($state.decision.risk_score))" -ForegroundColor $(if ($state.decision.risk_score -gt 70) { "Red" } elseif ($state.decision.risk_score -gt 40) { "Yellow" } else { "Green" })
    }
    
    if ($state.reputation_check) {
        Write-Host "Reputation: Known Scam = $($state.reputation_check.known_scam), Risk = $($state.reputation_check.risk_score)" -ForegroundColor Gray
    }
    
    # Show tools used in activity log
    $toolsUsed = $state.activity | Where-Object { $_.tool } | Select-Object -Unique -ExpandProperty tool
    if ($toolsUsed) {
        Write-Host "Tools used: $($toolsUsed -join ', ')" -ForegroundColor Cyan
    }
}
catch {
    Write-Host "Could not fetch final state: $_" -ForegroundColor Yellow
}

Write-Host "`nView in frontend: http://localhost:8080/calls/$CallSid" -ForegroundColor Cyan
Write-Host "Or check state: $BackendUrl/calls/$CallSid/state`n" -ForegroundColor Gray

