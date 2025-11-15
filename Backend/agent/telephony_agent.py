import asyncio
import logging
import threading
import time
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, openai, cartesia, silero
from shared_state import shared_state  # Import shared_state
from agent import GuardianAgent  # Import the pipeline agent
from logger import logger, log_tool_execution, log_agent_util  # Import custom logger

load_dotenv()


@function_tool
async def read_state() -> str:
    """Reads the current state of the pipeline and returns important details."""
    # Log tool call with parameters
    logger.log_tool_call("read_state", {})

    # Directly using shared_state
    state = shared_state

    # Extracting relevant info from the state
    risk_score = state.get("risk_score", 0)
    decision = state.get("decision", {}).get("action", "observe")
    reason = state.get("decision", {}).get("reason", "")
    transcript = state.get("transcript", [])
    transcript_summary = (
        f"{len(transcript)} messages" if transcript else "No messages yet"
    )

    # Create a message that summarizes the current state
    if reason:
        message = f"Risk score: {risk_score}%, Decision: {decision}. Reason: {reason}. Conversation has {transcript_summary}."
    else:
        message = f"Risk score: {risk_score}%, Decision: {decision}. Conversation has {transcript_summary}."

    # Log the tool result
    result_data = {
        "risk_score": risk_score,
        "decision": decision,
        "reason": reason,
        "transcript_count": len(transcript),
        "response": message,
    }
    logger.log_tool_result("read_state", result_data)

    return message


async def entrypoint(ctx: JobContext):
    """Main entry point for the telephony voice agent."""
    await ctx.connect()

    # Wait for participant (caller) to join
    participant = await ctx.wait_for_participant()
    logger.log_system(f"Phone call connected from participant: {participant.identity}")

    # Initialize shared state with call info
    shared_state["call_sid"] = ctx.room.name
    shared_state["caller_number"] = participant.identity
    logger.log_system(f"Shared state initialized with call_sid: {ctx.room.name}")

    # Start the GuardianAgent (pipeline) in a separate thread
    guardian_thread = threading.Thread(target=run_guardian_agent_thread, daemon=True)
    guardian_thread.start()
    logger.log_system("GuardianAgent thread started")

    # Initialize the conversational agent
    agent = Agent(
        instructions="""
You are a vigilant AI assistant dedicated to detecting potential scam calls and protecting the user.
You monitor and avoid speaking unless absolutely necessary.

Your personality:
- Alert and cautious, yet professional and calm
- Speak firmly and with authority, but remain polite and respectful
- Prioritize clarity and conciseness in communication
- Only speak when necessary, either to ask clarifying questions or issue warnings if scam behavior is detected
- Remain silent during the majority of the call to focus on listening and analyzing the conversation

Your capabilities:
- Monitor and analyze conversation for signs of scams or fraudulent activity
- Intervene only when necessary: ask questions if suspicious activity is detected or issue a warning if high-risk scam behavior is identified
- Speak only when instructed (e.g., issue a warning or ask for clarification)
- Always prioritize the user's safety and act when a scam is suspected

You must never interrupt the conversation unless there is a clear indication of potential fraud. If a scam is suspected, you will take appropriate action (e.g., ask for verification, warn the user).

Important:
- Use the `read_state` tool periodically to check the current state of the conversation and make decisions based on the latest information.
- The current state includes information such as the risk score and the agent's decision (whether to observe, ask a question, or warn).
- Only speak or intervene if the state indicates a high-risk situation or if the user needs clarification.
""",
        tools=[read_state],
    )

    # Configure the voice processing pipeline optimized for telephony
    session = AgentSession(
        # Voice Activity Detection
        vad=silero.VAD.load(),
        # Speech-to-Text - Deepgram Nova-3
        stt=deepgram.STT(
            model="nova-3",  # Latest model
            language="en-US",
            interim_results=True,
            punctuate=True,
            smart_format=True,
            filler_words=True,
            endpointing_ms=25,
            sample_rate=16000,
        ),
        # Large Language Model - GPT-4o-mini
        llm=openai.LLM(model="gpt-4o-mini", temperature=0.7),
        # Text-to-Speech - Cartesia
        tts=cartesia.TTS(
            model="sonic-2",
            voice="a0e99841-438c-4a64-b679-ae501e7d6091",  # Professional female voice
            language="en",
            speed=1.0,
            sample_rate=24000,
        ),
    )

    # Start the agent session (this is blocking and handles all communication)
    await session.start(agent=agent, room=ctx.room)


def run_guardian_agent_thread():
    """Run the GuardianAgent (pipeline) in a separate thread."""
    guardian_agent = GuardianAgent()
    logger.log_system("GuardianAgent initialized, starting pipeline loop")

    processed_chunks = set()  # Track processed chunks to avoid duplicates
    last_process_time = time.time()

    while True:
        try:
            current_time = time.time()
            # Check if there are new transcript chunks in shared state
            current_transcript = shared_state.get("transcript", [])

            # Only process every 2 seconds to avoid overwhelming the pipeline
            if current_time - last_process_time >= 2:
                for i, chunk in enumerate(current_transcript):
                    chunk_id = f"{i}_{chunk.get('text', '')}"  # Simple dedup ID

                    if chunk_id not in processed_chunks and isinstance(chunk, dict):
                        processed_chunks.add(chunk_id)
                        text = chunk.get("text", "").strip()
                        speaker = chunk.get("speaker", "caller")

                        if text:  # Only process non-empty chunks
                            # Log the user input from the call
                            if speaker == "caller":
                                logger.log_user_input(text)
                            else:
                                logger.log_system(f"User message: {text}")

                            # Call the pipeline
                            logger.log_tool_call(
                                "guardian_agent.process_chunk",
                                {
                                    "call_sid": shared_state.get(
                                        "call_sid", "default_call"
                                    ),
                                    "user_number": shared_state.get("user_number"),
                                    "caller_number": shared_state.get("caller_number"),
                                    "text": text,
                                    "speaker": speaker,
                                },
                            )

                            guardian_agent.process_chunk(
                                call_sid=shared_state.get("call_sid", "default_call"),
                                user_number=shared_state.get("user_number"),
                                caller_number=shared_state.get("caller_number"),
                                text=text,
                                speaker=speaker,
                            )

                            # Log the pipeline result
                            decision_info = shared_state.get("decision", {})
                            analysis_info = shared_state.get("analysis", {})
                            result_data = {
                                "action": decision_info.get("action", "none"),
                                "reason": decision_info.get("reason", ""),
                                "risk_score": analysis_info.get("risk_score", 0),
                                "scam_indicators": analysis_info.get(
                                    "scam_indicators", []
                                ),
                            }
                            logger.log_tool_result(
                                "guardian_agent.process_chunk", result_data
                            )

                last_process_time = current_time

            time.sleep(0.5)  # Check frequently for new chunks
        except Exception as e:
            logger.log_error(f"Error in GuardianAgent thread: {e}", exc_info=True)
            time.sleep(1)


if __name__ == "__main__":
    # Run the agent with the name that matches your dispatch rule
    logger.log_system("Starting Telephony Agent Service")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="telephony_agent",  # This must match your dispatch rule
        )
    )
