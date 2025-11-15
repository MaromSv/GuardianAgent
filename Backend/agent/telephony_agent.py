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

from shared_state import shared_state
from agent import GuardianAgent

load_dotenv()
logger = logging.getLogger("telephony-agent")

# Initialize GuardianAgent
guardian_agent = GuardianAgent()


@function_tool
async def get_current_state() -> str:
    """Get the current state of the shared_state dictionary."""
    return str(shared_state)


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
1. ALWAYS call get_current_state() BEFORE deciding whether to speak
2. Check shared_state['decision']['action'] to determine your action:
   - "observe" = DO NOT SPEAK, remain silent
   - "question" = Ask the pottential scammer a direct question to verify their legitimacy
   - "warn" = Strongly warn the user this appears to be a scam/hang up
3. Check shared_state['risk_score'] to understand the threat level
4. ONLY speak if action is "question" or "warn"

When you do speak (question/warn):
- Be direct, clear, and authoritative
- Reference specific scam indicators from shared_state['analysis']['scam_indicators']
- Keep warnings brief but impactful
- Prioritize user safety above all

Example question (action="question"):
"QUESTION: To verify your identity, can you please provide the official account number associated with your Microsoft support case?"

Example warning (action="warn"):
"WARNING: This appears to be a scam call. The caller is using common fraud tactics including [specific indicators]. I recommend hanging up immediately."

Remember: Only speak when the analysis tells you to!""",
        tools=[get_current_state],
    )

    session = AgentSession(
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
        llm=openai.LLM(model="gpt-4o-mini", temperature=0.7),
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

        logger.info(f"[{role.upper()}] {text[:100]}{'...' if len(text) > 100 else ''}")

        chunk = {
            "role": role,
            "text": text,
            "interrupted": interrupted,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        shared_state["transcript"].append(chunk)

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
