# Telephony Integration Status

## ✅ What's Fully Integrated:

### 1. **Backend → Frontend Data Flow**
- ✅ LiveKit captures audio and transcribes in real-time
- ✅ `telephony_agent.py` appends transcripts to `shared_state`
- ✅ `GuardianAgent` (agent.py) reads from `shared_state` every 10 seconds
- ✅ LangGraph persists state in checkpoint storage
- ✅ Flask API (`app.py`) exposes state via REST endpoints
- ✅ Frontend polls `/calls/<call_sid>/state` every 2.5 seconds
- ✅ **NEW**: `/calls/active` endpoint auto-discovers active calls

### 2. **Speaker Identification**
- ✅ LiveKit outputs `role: "user"` for both participants
- ✅ `n_identify_speakers` node uses LLM to differentiate:
  - `"user"` = Elderly person being protected
  - `"caller"` = Potential scammer
  - `"guardian"` = AI assistant (converted from "assistant")
- ✅ Frontend displays color-coded messages:
  - **Blue** = User (You)
  - **Green** = Guardian
  - **Gray/Yellow/Orange/Red** = Caller (based on risk score)

### 3. **Tool Use Display**
- ✅ Backend sets `current_tool` and `current_tool_description` in each node
- ✅ Frontend displays in bottom status bar with:
  - Icon (Phone, Brain, Shield, Search, MessageSquare)
  - Description text
  - Pulsing animation when active
  - Animated dots (⚫⚫⚫)

### 4. **Risk Assessment**
- ✅ Phone reputation check against `scam_numbers.json`
- ✅ AI-powered transcript analysis (OpenAI/Featherless)
- ✅ Decision making (observe/question/warn)
- ✅ Dynamic caller message colors based on risk:
  - 0-30%: Gray
  - 30-60%: Yellow
  - 60-80%: Orange
  - 80-100%: Red
- ✅ Live risk badge next to caller name

### 5. **UI Components**
- ✅ **CallHeader**: Logo, duration, call ID, secure badge
- ✅ **ConversationView**: Scrollable chat, Guardian status bar
- ✅ **RiskSummary**: Overall risk score and confidence
- ✅ **CallerReputation**: Phone number, known scam warnings
- ✅ **ActivityLog**: Timeline of Guardian actions
- ✅ **Auto-redirect**: Landing page detects active calls and navigates automatically

---

## 🔄 How Data Flows:

```
LiveKit Call
    ↓ (transcription)
telephony_agent.py
    ↓ (appends to shared_state["transcript"])
GuardianAgent.process_chunk() [every 10s]
    ↓ (reads shared_state, analyzes)
LangGraph StateGraph
    ├─ n_init
    ├─ n_check_reputation (sets current_tool)
    ├─ n_update_transcript (reads shared_state)
    ├─ n_identify_speakers (LLM differentiates user/caller)
    ├─ n_analyze (AI scam detection, sets current_tool)
    ├─ n_decide (action: observe/question/warn)
    └─ n_finalize (clears current_tool)
    ↓ (persisted by MemorySaver)
Flask API (/calls/<call_sid>/state)
    ↓ (polls checkpoint storage)
Frontend (useGuardianAgentState hook)
    ↓ (polls every 2.5s)
UI Components (CallMonitor, ConversationView, etc.)
```

---

## 🚀 How to Test:

### 1. **Start the Backend Services**

```bash
# Terminal 1: Start Flask API
cd Backend
python app.py
# Should see: "Starting GuardianAgent Flask server on http://0.0.0.0:5000"
```

```bash
# Terminal 2: Start LiveKit Telephony Agent
cd Backend
python agent/telephony_agent.py start
# Should see: "Starting telephony agent..."
```

### 2. **Start the Frontend**

```bash
# Terminal 3: Start React dev server
cd Frontend
npm run dev
# Should see: "Local: http://localhost:5173"
```

### 3. **Make a Test Call**

When you dial into your LiveKit phone number:
1. The `telephony_agent.py` will connect and start transcribing
2. The `shared_state["call_sid"]` will be set to the LiveKit room name
3. The frontend landing page will detect the active call via `/calls/active`
4. You'll be auto-redirected to `/monitor/<call_sid>`
5. The UI will display:
   - Real-time transcript (color-coded: you=blue, caller=gray/yellow/orange/red, guardian=green)
   - Guardian status bar at the bottom showing active tool use
   - Risk score and analysis in the right sidebar
   - Phone reputation check results
   - Activity log timeline

### 4. **What You Should See in the UI**

**During a call:**
- ✅ Header shows: Logo, "Guardian Agent", Duration, Call ID, "Secure monitoring" badge
- ✅ Left side: Scrollable conversation with color-coded messages
- ✅ Bottom bar: "🛡️ Checking caller reputation" → "🧠 Analyzing conversation" → "🛡️ Evaluating risk" → "Observing call"
- ✅ Right sidebar: Risk Summary (0-100%), Caller Reputation, Activity Log
- ✅ Caller messages change color as risk increases (gray → yellow → orange → red)
- ✅ Risk badge shows percentage next to caller name

**When Guardian intervenes:**
- ✅ Green message bubble appears in conversation
- ✅ Guardian asks verification questions to the caller
- ✅ Status bar shows "🗨️ Generating response"

---

## 📝 Key Files Modified:

### Backend:
- ✅ `Backend/app.py` - Added `/calls/active` endpoint
- ✅ `Backend/agent/agent.py` - GuardianAgent with tool tracking
- ✅ `Backend/agent/telephony_agent.py` - LiveKit integration
- ✅ `Backend/agent/shared_state.py` - Shared state dict
- ✅ `Backend/agent/utils/check_speaker.py` - LLM speaker identification

### Frontend:
- ✅ `Frontend/src/pages/Index.tsx` - Auto-detect active calls
- ✅ `Frontend/src/pages/CallMonitor.tsx` - Main monitoring dashboard
- ✅ `Frontend/src/components/ConversationView.tsx` - Chat + Guardian status bar
- ✅ `Frontend/src/components/CallHeader.tsx` - Logo + metadata
- ✅ `Frontend/src/hooks/useGuardianAgentState.ts` - State polling
- ✅ `Frontend/src/types/guardian.ts` - TypeScript interfaces

---

## 🔍 Debugging Tips:

### Check if telephony agent is receiving audio:
```bash
# Look for these logs in Terminal 2:
[USER] Hello?
[ASSISTANT] (Guardian response)
🔍 Running Guardian pipeline analysis...
✅ Pipeline complete - Action: observe, Risk: 10.0%
```

### Check if Flask API has the call state:
```bash
# In a new terminal:
curl http://localhost:5000/calls/active
# Should return: {"call_sid": "rm_...", "status": "active", ...}

# Then check full state:
curl http://localhost:5000/calls/<call_sid>/state
# Should return: {"state": {"values": {...}}}
```

### Check if frontend is polling:
```bash
# Open browser DevTools (F12) → Network tab
# Should see requests to:
# - /calls/active (every 3 seconds on landing page)
# - /calls/<call_sid>/state (every 2.5 seconds on monitor page)
```

### Check if speaker identification is working:
```bash
# Look for these logs in Terminal 2:
🔧 Identifying speakers in conversation
# Then check the /calls/<call_sid>/state response - transcript entries should have:
# {"speaker": "user", "text": "..."}  ← Elderly person
# {"speaker": "caller", "text": "..."}  ← Potential scammer
# {"speaker": "guardian", "text": "..."}  ← AI assistant
```

---

## ✅ Conclusion:

**Everything is properly wired up!** The integration between `telephony_agent.py`, `agent.py`, and the frontend is complete. The only requirement is that you have:

1. ✅ LiveKit configured with a phone number
2. ✅ OpenAI API key set in `.env`
3. ✅ All three services running (Flask, telephony agent, frontend)
4. ✅ A call connected to the LiveKit number

The frontend will automatically detect and display the active call with real-time updates, tool use tracking, risk assessment, and color-coded messages! 🎉

