from __future__ import annotations

from typing import TypedDict, Dict, Any, List, Optional
import uuid
import time
import json
import os

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from agent.utils.check_phone_reputation import check_reputation
from agent.utils.assess_scam_probability import analyze_transcript
from agent.utils.report_scam import add_scam_to_database
from agent.logger import logger
from agent.shared_state import shared_state, save_shared_state


class GuardianState(TypedDict, total=False):
    # Call / meta
    call_sid: str
    user_number: str
    caller_number: str
    call_started_at: float

    # Transcript
    transcript: List[Dict[str, str]]
    last_chunk: str
    speaker: str
    last_analysis_ts: float
    should_analyze_now: bool

    # Scam reputation
    reputation_check: Dict[str, Any]

    # Analysis
    analysis: Dict[str, Any]
    analysis_history: List[Dict[str, Any]]

    # Decision
    decision: Dict[str, Any]
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
    current_tool: str
    current_tool_description: str


def _log(state: GuardianState, stage: str, data: Dict[str, Any]) -> GuardianState:
    """Log an activity entry (only for important stages, not every transcript update)."""
    entry = {"stage": stage, "data": data}
    current_tool = state.get("current_tool")
    if current_tool:
        entry["tool"] = current_tool
    current_tool_desc = state.get("current_tool_description")
    if current_tool_desc:
        entry["tool_description"] = current_tool_desc

    # Only log to logger for important stages
    if stage in [
        "check_reputation",
        "analyze_transcript",
        "decide_action",
        "process_scam",
    ]:
        logger.log_tool_result(stage, entry)

    state.setdefault("activity", []).append(entry)
    return state


class GuardianAgent:
    """
    GuardianAgent pipeline using LangGraph.
    Runs every 10 seconds via timer in telephony_agent.py
    """

    def __init__(self, llm=None):
        self.llm = llm
        self.memory = MemorySaver()
        self._setup_graph()

    # ──────────────── Nodes ──────────────── #

    def n_init(self, state: GuardianState) -> GuardianState:
        """Ensure required keys exist and handle first-time setup per call."""
        now = time.time()

        # Ensure basics
        state.setdefault("transcript", [])
        state.setdefault("analysis_history", [])
        state.setdefault("activity", [])

        # First-time setup for this call
        if "call_started_at" not in state:
            state["call_started_at"] = now

        # Normalize speaker
        speaker = state.get("speaker") or "caller"
        state["speaker"] = speaker

        # Normalize last_chunk
        last_chunk = (state.get("last_chunk") or "").strip()
        state["last_chunk"] = last_chunk

        return state

    def n_check_reputation(self, state: GuardianState) -> GuardianState:
        """Check caller_number against scam database."""
        caller_number = state.get("caller_number")
        if not caller_number:
            return state

        if "reputation_check" not in state:
            state["current_tool"] = "phone_reputation_check"
            state["current_tool_description"] = (
                f"Checking phone number {caller_number} against scam database"
            )

            rep = check_reputation(caller_number)
            state["reputation_check"] = rep
            _log(state, "check_reputation", rep)

        return state

    def n_update_transcript(self, state: GuardianState) -> GuardianState:
        """
        Read raw transcript from shared_state and convert format.
        The telephony agent uses 'role', but analysis expects 'speaker'.
        """
        # Get raw transcript from shared_state (telephony_agent updates this)
        raw_transcript = shared_state.get("raw_transcript") or shared_state.get("transcript", [])

        # Convert format: support both {'role', 'text'} and already-processed {'speaker', 'text'}
        converted_transcript = []
        for entry in raw_transcript:
            speaker = entry.get("speaker") or entry.get("role", "unknown")
            converted_transcript.append(
                {"speaker": speaker, "text": entry.get("text", "")}
            )

        state["transcript"] = converted_transcript

        # Always analyze when invoked by timer
        state["should_analyze_now"] = True
        state["last_analysis_ts"] = time.time()

        return state

    def n_identify_speakers(self, state: GuardianState) -> GuardianState:
        """
        Identify speakers in transcript (distinguishing user vs caller).
        Uses LLM to analyze conversation context and properly label speakers.
        Only processes entries that need identification.
        """
        from agent.utils.check_speaker import identify_speakers, needs_speaker_identification
        
        transcript = state.get("transcript", [])
        
        # Skip if no identification needed
        if not transcript or not needs_speaker_identification(transcript):
            return state
        
        # Set current tool for UI
        state["current_tool"] = "speaker_identification"
        state["current_tool_description"] = "Identifying speakers in conversation"
        
        # Identify speakers (distinguishes user vs caller)
        updated_transcript = identify_speakers(
            transcript=transcript,
            user_number=state.get("user_number"),
            caller_number=state.get("caller_number"),
        )
        
        state["transcript"] = updated_transcript

        _log(
            state,
            "identify_speakers",
            {
                "msg": "Speaker identification complete",
                "transcript_length": len(updated_transcript),
            },
        )
        
        return state

    def n_analyze(self, state: GuardianState) -> GuardianState:
        """Analyze transcript for scam indicators using AI."""
        state["current_tool"] = "transcript_analysis"
        state["current_tool_description"] = "Analyzing conversation for scam indicators"

        analysis_obj = analyze_transcript(state["transcript"])
        state["analysis"] = analysis_obj
        state.setdefault("analysis_history", []).append(
            {"ts": time.time(), **analysis_obj}
        )
        _log(state, "analyze_transcript", analysis_obj)

        return state

    def n_decide(self, state: GuardianState) -> GuardianState:
        """Decide what GuardianAgent should do: observe, question, or warn."""
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

        # Build detailed reason
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

        state["current_tool"] = "decision_making"
        state["current_tool_description"] = "Evaluating risk and deciding on action"

        state["decision"] = decision
        state["stop_call"] = False
        state["should_continue"] = True

        _log(state, "decide_action", decision)

        return state

    def n_process_scam(self, state: GuardianState) -> GuardianState:
        """Process a detected scam by adding the number to the local database."""
        decision = state.get("decision") or {}
        caller_number = state.get("caller_number")
        risk = decision.get("risk_score")
        analysis = state.get("analysis") or {}

        # Only process once per call
        if state.get("scam_processed"):
            return state

        state["scam_processed"] = True

        result = add_scam_to_database(
            phone_number=caller_number,
            risk_score=risk,
            analysis=analysis,
            decision=decision,
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
        """Mark that an utterance should be generated."""
        decision = state.get("decision") or {}
        action = decision.get("action", "observe")

        if action == "observe":
            state["guardian_utterance_text"] = ""
            return state

        # Update shared state to signal telephony service to generate speech
        shared_state["decision"] = decision
        shared_state["action"] = action

        return state

    def n_finalize(self, state: GuardianState) -> GuardianState:
        """
        End-of-step bookkeeping.
        Update shared_state with analysis results for telephony agent to use.
        """
        # Update shared_state with the latest results
        shared_state["analysis"] = state.get("analysis", {})
        shared_state["decision"] = state.get("decision", {})
        shared_state["risk_score"] = state.get("decision", {}).get("risk_score", 0)

        summary = {
            "call_sid": state.get("call_sid"),
            "caller_number": state.get("caller_number"),
            "user_number": state.get("user_number"),
            "latest_risk": (state.get("analysis") or {}).get("risk_score"),
            "decision": state.get("decision"),
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
        builder.add_node("identify_speakers", self.n_identify_speakers)
        builder.add_node("analyze", self.n_analyze)
        builder.add_node("decide", self.n_decide)
        builder.add_node("process_scam", self.n_process_scam)
        builder.add_node("generate_utterance", self.n_generate_utterance)
        builder.add_node("finalize", self.n_finalize)

        builder.add_edge(START, "init")
        builder.add_edge("init", "check_reputation")
        builder.add_edge("check_reputation", "update_transcript")
        builder.add_edge("update_transcript", "identify_speakers")

        # After speaker identification, decide if we should analyze or just finalize
        def branch_after_identify(state: GuardianState):
            if state.get("should_analyze_now", False):
                return "analyze"
            else:
                return "skip_analysis"

        builder.add_conditional_edges(
            "identify_speakers",  # Changed from "update_transcript"
            branch_after_identify,
            {
                "analyze": "analyze",
                "skip_analysis": "finalize",
            },
        )

        builder.add_edge("analyze", "decide")

        # After decide, branch based on action
        def branch_after_decide(state: GuardianState):
            action = (state.get("decision") or {}).get("action", "observe")
            if action == "observe":
                return "skip_speech"
            elif action == "warn":
                return "process_scam"
            else:
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

        builder.add_edge("process_scam", "generate_utterance")
        builder.add_edge("generate_utterance", "finalize")
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
        Entry point for timer-based pipeline runs.
        Reads transcript from shared_state, analyzes it, updates shared_state with results.
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
                    "thread_id": thread_id or call_sid or str(uuid.uuid4()),
                }
            },
        )

        return result
