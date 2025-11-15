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

from utils.sms import send_family_alert_sms
from shared_state import shared_state
from agent import GuardianAgent

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

            # Log summary only
            decision = result.get("decision", {})
            logger.info(
                f"✅ Pipeline complete - Action: {decision.get('action', 'none')}, "
                f"Risk: {decision.get('risk_score', 0):.1f}%, "
                f"Reason: {decision.get('reason', 'N/A')}"
            )

    except asyncio.CancelledError:
        logger.info("⏹️  Guardian pipeline timer stopped")
        raise  # Re-raise to properly handle cancellation
    except Exception as e:
        logger.error(f"❌ Error in guardian pipeline: {e}", exc_info=True)


async def on_call_hangup(ctx: JobContext, pipeline_task: asyncio.Task):
    """
    Handle cleanup and final processing when a call is disconnected.

    Args:
        ctx: JobContext containing room and call information
        pipeline_task: The background guardian pipeline task to cancel
    """
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

        # If the call was determined to be a scam, send SMS alert to family member
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

    # Wait for participant (caller) to join
    participant = await ctx.wait_for_participant()
    logger.info(f"📞 Phone call connected from: {participant.identity}")

    # Initialize shared_state
    if "transcript" not in shared_state:
        shared_state["transcript"] = []

    # Set call metadata
    shared_state["caller_number"] = participant.identity
    shared_state["user_number"] = ctx.room.name
    shared_state["call_sid"] = ctx.room.name

    logger.info(f"🔧 Initialized shared_state for call: {ctx.room.name}")

    # Start the guardian pipeline timer in background
    pipeline_task = asyncio.create_task(guardian_pipeline_timer(ctx))

    agent = Agent(
        instructions="""You are a vigilant Guardian AI assistant dedicated to protecting users from scam calls.

CRITICAL RULES:
1. ALWAYS call get_current_state() BEFORE responding.
2. Read the "action" field from get_current_state():
   - "observe" = DO NOT SPEAK, return an empty string as your reply.
   - "question" = Ask the potential scammer a direct question to verify their legitimacy.
   - "warn" = Strongly warn the user this appears to be a scam and tell them to hang up.
3. Use "risk_score" and "reason" from get_current_state() to shape how strong your warning is.
4. NEVER speak if action == "observe". Your reply must be completely empty in that case.

When you do speak (question/warn):
- Be direct, clear, and authoritative
- Keep it short (1–2 sentences)
- Prioritize user safety above all

Example question (action="question"):
"QUESTION: To verify your identity, can you please provide the official account number associated with your Microsoft support case?"

Example warning (action="warn"):
"WARNING: This appears to be a scam call. The caller is using common fraud tactics. I recommend hanging up immediately."

Remember: Only speak when the analysis tells you to, and say NOTHING at all when action is "observe".""",
        tools=[get_current_state],
    )

    session = AgentSession(
        allow_interruptions=False,
        vad=silero.VAD.load(),
        stt=deepgram.STT(
            model="nova-3",
            language="en-US",
            interim_results=True,
            punctuate=True,
            smart_format=True,
            filler_words=True,
            endpointing_ms=25,
            sample_rate=16000,
        ),
        llm=openai.LLM(
            model="gpt-4o-mini",
            temperature=0.7,
            tool_choice="required",
        ),
        # tts=cartesia.TTS(
        #     model="sonic-2",
        #     voice="a0e99841-438c-4a64-b679-ae501e7d6091",
        #     language="en",
        #     speed=1.0,
        #     sample_rate=24000,
        # ),
        tts=elevenlabs.TTS(
            voice_id="ODq5zmih8GrVes37Dizd", model="eleven_multilingual_v2"
        ),
    )

    # ---- REALTIME USER STT (for logs / optional live transcript) ----
    @session.on("user_input_transcribed")
    def _on_user_input(ev: UserInputTranscribedEvent):
        # Only log final transcripts to reduce noise
        if ev.is_final:
            logger.info(f"[USER] {ev.transcript}")

            chunk = {
                "role": "user",
                "text": ev.transcript,
                "interrupted": False,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            shared_state["transcript"].append(chunk)

    # ---- FINAL MESSAGES FOR BOTH USER + ASSISTANT ----
    @session.on("conversation_item_added")
    def _on_conversation_item(ev: ConversationItemAddedEvent):
        role = ev.item.role
        text = ev.item.text_content or ""
        interrupted = ev.item.interrupted

        logger.info(f"[{role.upper()}] {text}")

        chunk = {
            "role": role,
            "text": text,
            "interrupted": interrupted,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        shared_state["transcript"].append(chunk)

    @ctx.room.on("participant_disconnected")
    def _on_participant_disconnected(disconnected_participant):
        logger.info(
            f"👋 participant_disconnected event: {disconnected_participant.identity}"
        )

        if disconnected_participant.identity == participant.identity:
            logger.info("📵 Caller hung up, running hangup logic...")
            asyncio.create_task(on_call_hangup(ctx, pipeline_task))
            ctx.shutdown(reason="caller_hangup")

    # Start the agent session
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
