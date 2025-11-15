import sys
import os

# Fix import path when running directly - MUST BE FIRST!
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
    UserInputTranscribedEvent,
    ConversationItemAddedEvent,
)
from livekit.plugins import deepgram, openai, cartesia, silero, elevenlabs

from agent.shared_state import shared_state, save_shared_state
from utils.sms import send_family_alert_sms
from agent.agent import GuardianAgent

load_dotenv()
logger = logging.getLogger("telephony-agent")

# Initialize GuardianAgent
guardian_agent = GuardianAgent()


@function_tool
async def get_current_state() -> dict:
    """Get the current guardian decision about whether you should speak.

    Returns a dict like:
    {
      "action": "observe" | "question" | "warn",
      "reason": "...",
      "risk_score": 0-100
    }
    """
    decision = shared_state.get("decision", {}) or {}
    return {
        "action": decision.get("action", "observe"),
        "reason": decision.get("reason", "No analysis yet"),
        "risk_score": float(decision.get("risk_score", 0.0)),
    }


async def guardian_pipeline_timer(ctx: JobContext):
    """Run GuardianAgent pipeline every 10 seconds."""
    call_sid = ctx.room.name
    logger.info(f"🔄 Starting Guardian pipeline timer for call: {call_sid}")

    try:
        while True:
            await asyncio.sleep(10)

            # Check if there's transcript data to analyze
            if not shared_state.get("transcript"):
                logger.info("⏭️  No transcript data yet, skipping analysis")
                continue

            # Ensure it starts off non suspecting
            shared_state["decision"] = {
                "action": "observe",
                "reason": "No analysis yet",
                "risk_score": 0.0,
            }

            logger.info("🔍 Running Guardian pipeline analysis...")

            # Run the pipeline - it will read from and update shared_state internally
            result = guardian_agent.process_chunk(
                call_sid=call_sid,
                user_number=shared_state.get("user_number"),
                caller_number=shared_state.get("caller_number"),
                text="",  # Empty text since we're analyzing existing transcript
                speaker="system",
                thread_id=call_sid,
            )

            # Update shared_state with latest processed state for UI
            decision = result.get("decision", {}) or {}
            analysis = result.get("analysis", {}) or {}
            processed_transcript = result.get("transcript") or []

            shared_state["analysis"] = analysis
            shared_state["decision"] = decision
            shared_state["risk_score"] = float(decision.get("risk_score", 0.0))

            # Update the transcript with properly identified speakers
            if processed_transcript:
                shared_state["transcript"] = processed_transcript
                logger.info(
                    f"📝 Updated transcript with speaker identification: {len(processed_transcript)} items"
                )

            # Persist to disk so Flask can serve it
            save_shared_state()

            # Log summary only
            logger.info(
                f"✅ Pipeline complete - Action: {decision.get('action', 'none')}, "
                f"Risk: {decision.get('risk_score', 0):.1f}%, "
                f"Reason: {decision.get('reason', 'N/A')}"
            )

    except asyncio.CancelledError:
        logger.info("⏹️  Guardian pipeline timer stopped")
        raise
    except Exception as e:
        logger.error(f"❌ Error in guardian pipeline: {e}", exc_info=True)


async def on_call_hangup(ctx: JobContext, pipeline_task: asyncio.Task):
    """Handle cleanup when call disconnects."""
    call_sid = ctx.room.name
    logger.info(f"📴 Call disconnected: {call_sid}")

    try:
        # Cancel the guardian pipeline timer
        if pipeline_task and not pipeline_task.done():
            pipeline_task.cancel()
            try:
                await pipeline_task
            except asyncio.CancelledError:
                logger.info("✅ Guardian pipeline timer cancelled successfully")

        # If scam detected, send SMS alert
        if shared_state.get("decision", {}).get("action") == "warn":
            family_number = "+31615869452"
            scam_details = shared_state.get("analysis", {}).get("reason", "")
            risk = shared_state["decision"].get("risk_score", 0)

            send_family_alert_sms(
                family_number=family_number,
                user_number=shared_state["user_number"],
                scam_details=scam_details,
                risk_score=risk,
            )

        logger.info(f"🏁 Hangup processing complete for call: {call_sid}")

    except Exception as e:
        logger.error(f"❌ Error during hangup processing: {e}", exc_info=True)


async def entrypoint(ctx: JobContext):
    """Main entry point for the telephony voice agent."""
    await ctx.connect()

    # Wait for participants
    logger.info("⏳ Waiting for participants to join...")
    participants = []

    first_participant = await ctx.wait_for_participant()
    participants.append(first_participant)
    logger.info(f"📞 First participant joined: {first_participant.identity}")

    try:
        second_participant = await asyncio.wait_for(
            ctx.wait_for_participant(), timeout=5.0
        )
        participants.append(second_participant)
        logger.info(f"📞 Second participant joined: {second_participant.identity}")
    except asyncio.TimeoutError:
        logger.warning(
            "⚠️  No second participant within 5s, continuing with single participant"
        )
        second_participant = None

    # Initialize shared_state
    shared_state["raw_transcript"] = []
    shared_state["transcript"] = []
    shared_state["caller_number"] = first_participant.identity
    shared_state["user_number"] = (
        second_participant.identity if second_participant else ctx.room.name
    )
    shared_state["call_sid"] = ctx.room.name

    save_shared_state()

    logger.info(f"🔧 Initialized shared_state for call: {ctx.room.name}")
    logger.info(f"   Caller: {shared_state['caller_number']}")
    logger.info(f"   Protected user: {shared_state['user_number']}")

    # Start background tasks
    pipeline_task = asyncio.create_task(guardian_pipeline_timer(ctx))
    processed_transcripts = set()

    # Helper for async speaker identification
    async def _identify_speaker_async():
        try:
            from agent.utils.check_speaker import identify_speakers

            identified_transcript = await asyncio.get_event_loop().run_in_executor(
                None,
                identify_speakers,
                shared_state["transcript"],
                shared_state.get("user_number"),
                shared_state.get("caller_number"),
            )
            shared_state["transcript"] = identified_transcript
            save_shared_state()
            logger.debug("✅ Speaker labels refined")
        except Exception as e:
            logger.debug(f"Speaker ID skipped: {e}")

    def _add_transcript(speaker: str, text: str, interrupted: bool = False):
        """Add transcript entry immediately."""
        chunk = {
            "speaker": speaker,
            "text": text,
            "interrupted": interrupted,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        shared_state.setdefault("raw_transcript", []).append(chunk)
        shared_state.setdefault("transcript", []).append(chunk)
        save_shared_state()
        logger.info(f"💾 [{speaker.upper()}] {text[:60]}...")

        # Trigger speaker identification for human messages
        # (will use LLM to distinguish "user" vs "pottential_scammer")
        if speaker == "user":
            asyncio.create_task(_identify_speaker_async())

    agent = Agent(
        instructions="""You are a Guardian AI protecting users from scam calls.

RULES:
1. ALWAYS call get_current_state() BEFORE responding
2. Based on "action":
   - "observe" = DO NOT SPEAK (return empty string)
   - "question" = Ask scammer verification question
   - "warn" = Strongly warn user to hang up
3. Keep responses short (1-2 sentences)

Afer asking a question, if the scammer provides a good awnser, revert to action="observe".
Introduce yourselelf as Guardian Agent only once the very first time you speak.

NEVER speak when action="observe".""",
        tools=[get_current_state],
    )

    session = AgentSession(
        allow_interruptions=False,
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3", language="en"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(
            voice_id="ODq5zmih8GrVes37Dizd", model="eleven_multilingual_v2"
        ),
    )

    # ===== CAPTURE ALL USER SPEECH (REAL-TIME) =====
    @session.on("user_input_transcribed")
    def _on_user_input(ev: UserInputTranscribedEvent):
        if not ev.is_final or not ev.transcript.strip():
            return

        text = ev.transcript.strip()
        transcript_id = f"{text}_{datetime.utcnow().timestamp()}"

        if transcript_id in processed_transcripts:
            return

        processed_transcripts.add(transcript_id)
        logger.info(f"🎤 [SPEECH] {text}")
        # Use "role" instead of "speaker" - let check_speaker.py identify the actual speaker
        _add_transcript(speaker="user", text=text, interrupted=False)

    # ===== CAPTURE AGENT RESPONSES & BACKUP USER MESSAGES =====
    @session.on("conversation_item_added")
    def _on_conversation_item(ev: ConversationItemAddedEvent):
        role = ev.item.role
        text = ev.item.text_content or ""
        interrupted = ev.item.interrupted

        if not text.strip():
            return

        # Always add agent responses
        if role == "assistant":
            logger.info(f"🤖 [AGENT] {text}")
            _add_transcript(speaker="agent", text=text, interrupted=interrupted)
            return

        # For user messages, check if already captured
        recent_texts = [
            t.get("text", "")
            for t in shared_state.get("transcript", [])[-5:]
            if t.get("speaker") in ["caller", "user", "pottential_scammer"]
        ]

        if text not in recent_texts:
            logger.info(f"👤 [USER-CONV] {text}")
            # Use "user" role - let check_speaker.py identify if it's caller or protected user
            _add_transcript(speaker="user", text=text, interrupted=interrupted)

    @ctx.room.on("participant_disconnected")
    def _on_participant_disconnected(disconnected_participant):
        logger.info(f"👋 Participant disconnected: {disconnected_participant.identity}")

        if disconnected_participant.identity in [p.identity for p in participants]:
            logger.info("📵 Running hangup logic...")
            asyncio.create_task(on_call_hangup(ctx, pipeline_task))
            ctx.shutdown(reason="participant_hangup")

    # Start session
    await session.start(agent=agent, room=ctx.room)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="telephony_agent",
        )
    )
