# guardian_agent.py
from __future__ import annotations

from typing import TypedDict, Dict, Any, List, Optional
import uuid
import time
import json
import os

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from .utils.check_phone_reputation import check_reputation
from .utils.assess_scam_probability import analyze_transcript
from .utils.agent_script import generate_guardian_message
from .utils.tts import placeholder_text_to_speech
from .utils.report_scam import add_scam_to_database
from .logger import logger


class GuardianState(TypedDict, total=False):
    # Call / meta
    call_sid: str
    user_number: str  # older person's number
    caller_number: str  # unknown caller
    call_started_at: float  # epoch seconds

    # Transcript
    transcript: List[Dict[str, str]]  # [{ "speaker": "...", "text": "..." }]
    last_chunk: str
    speaker: str  # "caller" | "user"
    last_analysis_ts: float  # epoch seconds of last analysis
    should_analyze_now: bool

    # Scam reputation
    reputation_check: Dict[str, Any]  # { "risk_score": float, "known_scam": bool, ... }

    # Analysis
    analysis: Dict[str, Any]  # latest analysis result
    analysis_history: List[Dict[str, Any]]

    # Decision
    decision: Dict[str, Any]  # { "action": "observe"|"question"|"warn", "reason": str }
    should_continue: bool
    stop_call: bool

    # Guardian speech
    guardian_utterance_text: str
    guardian_utterance_audio_url: str

    # Dealing with detected scam
    scam_processed: bool
    scam_report_result: Dict[str, Any]

    # Activity log for UI/debug
    activity: List[Dict[str, Any]]
    
    # Current tool being used (for UI display)
    current_tool: str  # e.g., "phone_reputation_check", "transcript_analysis", "web_search", "decision_making", None
    current_tool_description: str  # Human-readable description of what the tool is doing


def _log(state: GuardianState, stage: str, data: Dict[str, Any]) -> GuardianState:
    """
    Log an activity entry. Includes current_tool info if set (for historical record).
    """
    entry = {"stage": stage, "data": data}
    # Include current tool info if it's set (for historical record)
    current_tool = state.get("current_tool")
    if current_tool:
        entry["tool"] = current_tool
    current_tool_desc = state.get("current_tool_description")
    if current_tool_desc:
        entry["tool_description"] = current_tool_desc
    logger.log_tool_result(stage, entry)
    state.setdefault("activity", []).append(entry)
    return state


class GuardianAgent:
    """
    GuardianAgent pipeline using LangGraph, with nodes that:
      - init state
      - update transcript
      - periodically analyze for scam (every ANALYZE_INTERVAL_SECONDS)
      - decide on action (observe / question / warn)
      - for high risk (warn): process scam
      - optionally generate Guardian speech (text + audio)

    The “loop” is:
      - your backend calls process_chunk(...) repeatedly (e.g. per transcript chunk)
      - n_update_transcript decides if enough time has passed to re-run n_analyze
      - whenever risk is high enough, n_generate_utterance creates speech
    """

    # This is your "loop interval": how often we re-analyze transcript
    # Can be overridden via environment variable for testing
    ANALYZE_INTERVAL_SECONDS = int(os.getenv("GUARDIAN_ANALYZE_INTERVAL", "30"))

    def __init__(self, llm=None):
        self.llm = llm  # reserved for later, e.g., real OpenAI client
        self.memory = MemorySaver()
        self._setup_graph()

    # ──────────────── Nodes ──────────────── #

    def n_init(self, state: GuardianState) -> GuardianState:
        """
        Ensure required keys exist and handle first-time setup per call.
        This runs on every graph invocation (e.g., every transcript chunk or timer tick).
        """
        now = time.time()

        # Ensure basics
        state.setdefault("transcript", [])
        state.setdefault("analysis_history", [])
        state.setdefault("activity", [])

        # First-time setup for this call
        if "call_started_at" not in state:
            state["call_started_at"] = now
            _log(
                state,
                "init_call",
                {
                    "msg": "Initialized new call state",
                    "call_sid": state.get("call_sid"),
                    "caller_number": state.get("caller_number"),
                    "user_number": state.get("user_number"),
                },
            )

        # Normalize speaker
        speaker = state.get("speaker") or "caller"
        state["speaker"] = speaker

        # Normalize last_chunk
        last_chunk = (state.get("last_chunk") or "").strip()
        state["last_chunk"] = last_chunk

        return state

    def n_check_reputation(self, state: GuardianState) -> GuardianState:
        """
        Check caller_number against a placeholder scam DB.
        Only needed once per call, but cheap enough to run every time.
        """
        caller_number = state.get("caller_number")
        if not caller_number:
            return state

        if "reputation_check" not in state:
            # Set current tool for UI
            state["current_tool"] = "phone_reputation_check"
            state["current_tool_description"] = f"Checking phone number {caller_number} against scam database"
            
            rep = check_reputation(caller_number)
            state["reputation_check"] = rep
            _log(state, "check_reputation", rep)

        return state

    def n_update_transcript(self, state: GuardianState) -> GuardianState:
        """
        Append last_chunk to transcript and decide if it's time to analyze again.

        This is the “loop point”: every time your backend calls process_chunk(),
        this node runs and sets should_analyze_now based on ANALYZE_INTERVAL_SECONDS.
        """
        last_chunk = state.get("last_chunk") or ""
        speaker = state.get("speaker") or "caller"

        if last_chunk:
            state["transcript"].append(
                {
                    "speaker": speaker,
                    "text": last_chunk,
                }
            )
            _log(
                state,
                "update_transcript",
                {"speaker": speaker, "text": last_chunk},
            )

        # Decide if we should analyze now
        now = time.time()
        last_ts = state.get("last_analysis_ts", 0.0)

        if now - last_ts >= self.ANALYZE_INTERVAL_SECONDS:
            state["should_analyze_now"] = True
        else:
            state["should_analyze_now"] = False

        return state

    def n_analyze(self, state: GuardianState) -> GuardianState:
        """
        Analyze transcript for scam indicators using AI.
        """
        # Set current tool for UI
        state["current_tool"] = "transcript_analysis"
        state["current_tool_description"] = "Analyzing conversation for scam indicators"
        
        analysis_obj = analyze_transcript(state["transcript"])
        state["analysis"] = analysis_obj
        state.setdefault("analysis_history", []).append(
            {"ts": time.time(), **analysis_obj}
        )
        state["last_analysis_ts"] = time.time()
        _log(state, "analyze_transcript", analysis_obj)
        
        return state

    def n_decide(self, state: GuardianState) -> GuardianState:
        """
        Decide what GuardianAgent should do:
          - observe
          - question
          - warn
        Based on AI transcript analysis and phone reputation database.
        """
        analysis = state.get("analysis") or {}
        rep = state.get("reputation_check") or {}

        transcript_risk = analysis.get("risk_score", 0.0)
        phone_risk = rep.get("risk_score", 0.0)
        risk = max(transcript_risk, phone_risk)

        if risk >= 80:
            action = "warn"
        elif risk >= 40:
            action = "question"
        else:
            action = "observe"

        # Build detailed reason showing which source contributed most
        if phone_risk > 0 and transcript_risk > 0:
            if phone_risk >= transcript_risk:
                if rep.get("known_scam"):
                    reason_text = f"High risk={risk:.0f}% (known scam database match). Conversation analysis: {transcript_risk:.0f}%"
                else:
                    reason_text = f"Combined risk={risk:.0f}% (phone: {phone_risk:.0f}%, conversation: {transcript_risk:.0f}%)"
            else:
                reason_text = f"High risk={risk:.0f}% from conversation analysis. Phone reputation: {phone_risk:.0f}%"
        elif phone_risk > 0:
            if rep.get("known_scam"):
                reason_text = f"Known scam number detected (risk: {phone_risk:.0f}%)"
            else:
                reason_text = f"Phone reputation risk: {phone_risk:.0f}%"
        elif transcript_risk > 0:
            reason_text = f"Conversation analysis risk: {transcript_risk:.0f}%"
        else:
            reason_text = "No risk detected"

        decision = {
            "action": action,
            "reason": reason_text,
            "risk_score": risk,
        }

        # Set current tool for UI
        state["current_tool"] = "decision_making"
        state["current_tool_description"] = "Evaluating risk and deciding on action"
        
        # For now, we never auto-stop the call
        state["decision"] = decision
        state["stop_call"] = False
        state["should_continue"] = True  # placeholder for future more complex loops

        _log(state, "decide_action", decision)
        
        return state

    def n_process_scam(self, state: GuardianState) -> GuardianState:
        """
        Process a detected scam by adding the number to the local database.
        This runs when we are confident this is a scam (action == 'warn').
        
        The number will be added to scam_numbers.json for future detection.
        """
        decision = state.get("decision") or {}
        caller_number = state.get("caller_number")
        risk = decision.get("risk_score")
        analysis = state.get("analysis") or {}

        # Only process once per call
        if state.get("scam_processed"):
            _log(
                state,
                "process_scam",
                {
                    "msg": "Scam already processed, skipping.",
                    "caller_number": caller_number,
                },
            )
            return state

        state["scam_processed"] = True

        # Add the scam number to our local database
        result = add_scam_to_database(
            phone_number=caller_number,
            risk_score=risk,
            analysis=analysis,
            decision=decision
        )

        scam_data = {
            "caller_number": caller_number,
            "risk_score": risk,
            "decision": decision,
            "database_update": result,
            "note": result.get("message", "Scam processing completed"),
        }

        state["scam_report_result"] = scam_data

        _log(state, "process_scam", scam_data)
        return state

    def n_generate_utterance(self, state: GuardianState) -> GuardianState:
        """
        Generate Guardian intervention message using AI.
        Only runs if decision.action != "observe".
        """
        decision = state.get("decision") or {}
        action = decision.get("action", "observe")
        if action == "observe":
            # No speech needed
            state["guardian_utterance_text"] = ""
            _log(
                state,
                "generate_utterance",
                {"msg": "Skipping utterance (observe only)."},
            )
            return state

        # Set current tool for UI
        state["current_tool"] = "speech_generation"
        state["current_tool_description"] = "Generating Guardian intervention message"
        
        text = generate_guardian_message(
            state["transcript"],
            state.get("analysis") or {},
        )
        state["guardian_utterance_text"] = text
        
        # Add Guardian message to transcript so it appears as a normal chat bubble
        state["transcript"].append({
            "speaker": "guardian",
            "text": text,
        })
        
        _log(state, "generate_utterance", {"utterance": text})
        
        return state

    def n_tts(self, state: GuardianState) -> GuardianState:
        """
        Convert GuardianAgent text into an audio URL (placeholder).
        """
        text = state.get("guardian_utterance_text") or ""
        if not text:
            state["guardian_utterance_audio_url"] = ""
            return state

        audio_url = placeholder_text_to_speech(text)
        state["guardian_utterance_audio_url"] = audio_url
        _log(state, "tts", {"audio_url": audio_url})
        return state

    def n_finalize(self, state: GuardianState) -> GuardianState:
        """
        End-of-step bookkeeping. In a real system, you might sync final risk score
        to a DB here. For now it's mostly a logging node.
        """
        summary = {
            "call_sid": state.get("call_sid"),
            "caller_number": state.get("caller_number"),
            "user_number": state.get("user_number"),
            "latest_risk": (state.get("analysis") or {}).get("risk_score"),
            "decision": state.get("decision"),
            "audio_url": state.get("guardian_utterance_audio_url"),
            "scam_processed": state.get("scam_processed", False),
        }
        _log(state, "finalize_step", summary)
        
        # Clear tool status after workflow completes
        state["current_tool"] = ""
        state["current_tool_description"] = ""
        
        return state

    # ─────────────────────────── Graph wiring ─────────────────────────── #

    def _setup_graph(self):
        builder = StateGraph(GuardianState)

        builder.add_node("init", self.n_init)
        builder.add_node("check_reputation", self.n_check_reputation)
        builder.add_node("update_transcript", self.n_update_transcript)
        builder.add_node("analyze", self.n_analyze)
        builder.add_node("decide", self.n_decide)
        builder.add_node("process_scam", self.n_process_scam)
        builder.add_node("generate_utterance", self.n_generate_utterance)
        builder.add_node("tts", self.n_tts)
        builder.add_node("finalize", self.n_finalize)

        builder.add_edge(START, "init")
        builder.add_edge("init", "check_reputation")
        builder.add_edge("check_reputation", "update_transcript")

        # After updating transcript, decide if we should analyze or just finalize
        def branch_after_update(state: GuardianState):
            if state.get("should_analyze_now", False):
                return "analyze"
            else:
                return "skip_analysis"

        builder.add_conditional_edges(
            "update_transcript",
            branch_after_update,
            {
                "analyze": "analyze",
                "skip_analysis": "finalize",
            },
        )

        # If we analyzed, we then decide what to do
        builder.add_edge("analyze", "decide")

        # After decide, branch based on action
        # - observe  -> no speech, straight to finalize
        # - warn     -> process_scam, then generate speech
        # - question -> generate speech
        def branch_after_decide(state: GuardianState):
            action = (state.get("decision") or {}).get("action", "observe")
            if action == "observe":
                return "skip_speech"
            elif action == "warn":
                return "process_scam"
            else:
                # "question" or any other action
                return "speak"

        builder.add_conditional_edges(
            "decide",
            branch_after_decide,
            {
                "skip_speech": "finalize",
                "process_scam": "process_scam",
                "speak": "generate_utterance",
            },
        )

        # If we processed scam, we still want to speak (warn the user)
        builder.add_edge("process_scam", "generate_utterance")

        builder.add_edge("generate_utterance", "tts")
        builder.add_edge("tts", "finalize")
        builder.add_edge("finalize", END)

        self.graph = builder.compile(checkpointer=self.memory)

    # ─────────────────────────── Runner API ─────────────────────────── #

    def process_chunk(
        self,
        *,
        call_sid: str,
        user_number: Optional[str],
        caller_number: Optional[str],
        text: str,
        speaker: str = "caller",
        thread_id: Optional[str] = None,
    ) -> GuardianState:
        """
        Entry point for each transcript chunk.

        In your Flask endpoint, you'd do something like:

            agent = GuardianAgent()
            state = agent.process_chunk(
                call_sid=call_sid,
                user_number=user_number,
                caller_number=caller_number,
                text=chunk_text,
                speaker="caller",
                thread_id=call_sid,
            )

        Then inspect `state["decision"]` and `state["guardian_utterance_audio_url"]`.
        """
        initial: GuardianState = {
            "call_sid": call_sid,
            "user_number": user_number or "",
            "caller_number": caller_number or "",
            "last_chunk": text,
            "speaker": speaker,
        }

        result: GuardianState = self.graph.invoke(
            initial,
            config={
                "configurable": {
                    # tie the graph state to this call
                    "thread_id": thread_id
                    or call_sid
                    or str(uuid.uuid4()),
                }
            },
        )

        msg = (
            f"Processed chunk for call_sid={call_sid}, "
            f"decision={result.get('decision')}, "
            f"audio_url={result.get('guardian_utterance_audio_url')!r}"
        )
        logger.log_agent_response("GuardianAgent", msg)
        return result


# ────────────────────────────── Example usage ────────────────────────────── #

if __name__ == "__main__":
    # Example: simulate a call getting a few transcript chunks.
    agent = GuardianAgent()

    call_sid = "CA1234567890"
    user_number = "+15550001111"
    caller_number = "+155599999999"  # ends with 9999 -> high risk in placeholder

    chunks = [
        "Hello, I am calling from your bank.",
        "We detected unusual activity and need your card number.",
        "Please also confirm your password and social security number.",
    ]

    for chunk in chunks:
        state = agent.process_chunk(
            call_sid=call_sid,
            user_number=user_number,
            caller_number=caller_number,
            text=chunk,
            speaker="caller",
            thread_id=call_sid,
        )
        # In a real backend, you'd now act on:
        #   state["decision"], state["guardian_utterance_audio_url"], etc.
