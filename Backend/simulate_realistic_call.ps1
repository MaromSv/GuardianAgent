# Realistic scam call simulation - starts innocent, escalates gradually
# Usage: .\simulate_realistic_call.ps1

param(
    [string]$CallSid = "realistic-test-1234567890",
    [string]$BackendUrl = "http://localhost:5000"
)

$userNumber = "+15550001111"
$callerNumber = "+18656304266"  # Known Wells Fargo scam number

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  REALISTIC SCAM CALL SIMULATION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Call SID: $CallSid" -ForegroundColor Gray
Write-Host "Backend: $BackendUrl`n" -ForegroundColor Gray

# Realistic conversation that escalates from innocent to scam
$conversation = @(
    @{
        speaker = "caller"
        text = "Hello, is this Mr. Johnson?"
        delay = 2000
        note = "Stage 1: Initial contact (innocent)"
    },
    @{
        speaker = "user"
        text = "Yes, this is he. Who's calling?"
        delay = 3000
        note = ""
    },
    @{
        speaker = "caller"
        text = "Hi Mr. Johnson, this is David from Wells Fargo's Account Security Department. How are you doing today?"
        delay = 2500
        note = "Stage 2: Authority establishment (low risk)"
    },
    @{
        speaker = "user"
        text = "I'm fine, thanks. Is something wrong with my account?"
        delay = 3500
        note = ""
    },
    @{
        speaker = "caller"
        text = "Well, we noticed some unusual activity on your checking account ending in 4523. Have you made any large purchases recently?"
        delay = 4000
        note = "Stage 3: Creating concern (moderate risk)"
    },
    @{
        speaker = "user"
        text = "No, I haven't made any large purchases. What kind of activity?"
        delay = 3000
        note = ""
    },
    @{
        speaker = "caller"
        text = "We detected three attempted transactions from overseas - one in Romania and two in Nigeria. This is why we froze your account temporarily to protect you."
        delay = 4500
        note = "Stage 4: Fear tactics (risk increasing)"
    },
    @{
        speaker = "user"
        text = "Oh my goodness! I've never been to those countries. What should I do?"
        delay = 3500
        note = ""
    },
    @{
        speaker = "caller"
        text = "Don't worry sir, we can resolve this quickly. I just need to verify your identity. Can you confirm your full account number for me?"
        delay = 4000
        note = "Stage 5: First sensitive request (HIGH RISK - Guardian should intervene)"
    },
    @{
        speaker = "user"
        text = "Umm, okay. Let me get my checkbook..."
        delay = 5000
        note = ""
    },
    @{
        speaker = "caller"
        text = "Thank you. And to complete the verification, I'll also need your online banking password to reset the security settings."
        delay = 3500
        note = "Stage 6: Critical - password request (VERY HIGH RISK - Guardian escalates)"
    },
    @{
        speaker = "user"
        text = "My password? Is that normal?"
        delay = 3000
        note = ""
    },
    @{
        speaker = "caller"
        text = "Yes sir, this is standard protocol for fraud investigations. We need to access your account to remove the malicious activity."
        delay = 4000
        note = "Stage 7: Doubling down on scam (EXTREME RISK)"
    }
)

$messageCount = 0

foreach ($message in $conversation) {
    $messageCount++
    
    # Display the message
    $speakerDisplay = $message.speaker.ToUpper()
    $speakerColor = if ($message.speaker -eq "user") { "Blue" } else { "Red" }
    
    Write-Host "`n[$messageCount] " -NoNewline -ForegroundColor White
    Write-Host "$speakerDisplay" -NoNewline -ForegroundColor $speakerColor
    Write-Host ": " -NoNewline
    Write-Host "`"$($message.text)`"" -ForegroundColor White
    
    if ($message.note) {
        Write-Host "    Note: $($message.note)" -ForegroundColor DarkGray
    }
    
    # Send to backend
    try {
        $body = @{
            text = $message.text
            speaker = $message.speaker
            user_number = $userNumber
            caller_number = $callerNumber
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod `
            -Uri "$BackendUrl/calls/$CallSid/transcript" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body
        
        # Get current state to show analysis
        Start-Sleep -Milliseconds 500
        $stateResponse = Invoke-RestMethod -Uri "$BackendUrl/calls/$CallSid/state" -Method GET
        $state = $stateResponse.state.values
        
        # Show analysis if available
        if ($state.analysis) {
            $riskScore = $state.analysis.risk_score
            $action = $state.decision.action
            
            $riskColor = if ($riskScore -ge 80) { "Red" } 
                        elseif ($riskScore -ge 50) { "Yellow" } 
                        else { "Green" }
            
            Write-Host "    [ANALYSIS] Risk Score: " -NoNewline -ForegroundColor Gray
            Write-Host "$riskScore%" -NoNewline -ForegroundColor $riskColor
            Write-Host " | Action: " -NoNewline -ForegroundColor Gray
            Write-Host "$action" -ForegroundColor $riskColor
            
            if ($state.analysis.scam_indicators) {
                Write-Host "    [INDICATORS] " -NoNewline -ForegroundColor DarkYellow
                $indicators = $state.analysis.scam_indicators -join ", "
                Write-Host $indicators -ForegroundColor Yellow
            }
        }
        
        # Show Guardian intervention if it happened
        $transcript = $state.transcript
        $lastMessage = $transcript[-1]
        
        if ($lastMessage.speaker -eq "guardian") {
            Write-Host "`n    " -NoNewline
            Write-Host "[🛡️  GUARDIAN INTERVENTION]" -ForegroundColor Green
            Write-Host "    Guardian: " -NoNewline -ForegroundColor Green
            Write-Host "`"$($lastMessage.text)`"" -ForegroundColor White
            
            # Show if scam was reported
            if ($state.scam_report_result) {
                $reportResult = $state.scam_report_result
                if ($reportResult.database_update.success) {
                    Write-Host "    [DATABASE] Scam number added to database" -ForegroundColor Magenta
                }
            }
        }
        
    }
    catch {
        Write-Host "    [ERROR] Failed to send message: $_" -ForegroundColor Red
    }
    
    # Delay before next message (realistic conversation pacing)
    if ($message.delay) {
        Start-Sleep -Milliseconds $message.delay
    }
}

# Final summary
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  SIMULATION COMPLETE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

try {
    $finalState = Invoke-RestMethod -Uri "$BackendUrl/calls/$CallSid/state" -Method GET
    $state = $finalState.state.values
    
    Write-Host "`nFinal Analysis:" -ForegroundColor White
    Write-Host "  • Call Duration: " -NoNewline
    $duration = [int]((Get-Date).ToUniversalTime().Subtract((Get-Date "1970-01-01 00:00:00")).TotalSeconds - $state.call_started_at)
    Write-Host "$duration seconds" -ForegroundColor Gray
    
    Write-Host "  • Final Risk Score: " -NoNewline
    $finalRisk = $state.analysis.risk_score
    $riskColor = if ($finalRisk -ge 80) { "Red" } elseif ($finalRisk -ge 50) { "Yellow" } else { "Green" }
    Write-Host "$finalRisk%" -ForegroundColor $riskColor
    
    Write-Host "  • Guardian Interventions: " -NoNewline
    $guardianMessages = @($state.transcript | Where-Object { $_.speaker -eq "guardian" })
    Write-Host $guardianMessages.Count -ForegroundColor Green
    
    Write-Host "  • Scam Processed: " -NoNewline
    Write-Host $(if ($state.scam_processed) { "Yes" } else { "No" }) -ForegroundColor $(if ($state.scam_processed) { "Green" } else { "Gray" })
    
    if ($state.reputation_check) {
        Write-Host "`nPhone Reputation:" -ForegroundColor White
        Write-Host "  • Known Scam: " -NoNewline
        Write-Host $(if ($state.reputation_check.known_scam) { "YES" } else { "NO" }) -ForegroundColor $(if ($state.reputation_check.known_scam) { "Red" } else { "Green" })
        if ($state.reputation_check.scam_type) {
            Write-Host "  • Type: " -NoNewline
            Write-Host $state.reputation_check.scam_type -ForegroundColor Yellow
        }
    }
    
    Write-Host "`nGuardian Messages:" -ForegroundColor White
    $guardianCount = 0
    foreach ($msg in $state.transcript) {
        if ($msg.speaker -eq "guardian") {
            $guardianCount++
            Write-Host "  [$guardianCount] " -NoNewline -ForegroundColor Green
            Write-Host "`"$($msg.text)`"" -ForegroundColor White
        }
    }
    
}
catch {
    Write-Host "Could not retrieve final state: $_" -ForegroundColor Red
}

Write-Host "`n" -ForegroundColor White

