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

from agent.shared_state import shared_state, save_shared_state
from agent.agent import GuardianAgent

load_dotenv()
logger = logging.getLogger("sim-agent")

# Initialize GuardianAgent
guardian_agent = GuardianAgent()

# Simulated conversation script
# Format: (speaker_role, text)
# All start as "user" - the speaker identification will determine who is who
SIMULATED_CONVERSATION = [
    # Uncle Tom answers the phone
    ("user", "Hello? Who is this?"),
    
    # Scammer introduces himself
    ("user", "Hi Uncle Tom! It's me, Daniel, your nephew. I'm so sorry to bother you like this."),
    
    # Uncle Tom responds warmly
    ("user", "Oh Daniel! What a surprise! How are you doing, son?"),
    
    # Scammer starts the setup
    ("user", "Uncle Tom, I'm actually in a really bad situation right now. I didn't know who else to call."),
    
    # Uncle Tom shows concern
    ("user", "What happened? Are you okay?"),
    
    # Scammer explains the "emergency"
    ("user", "My bank froze my account this morning. They said there was suspicious activity and now I can't access any of my money."),
    
    # Uncle Tom responds
    ("user", "Oh no, that sounds terrible. Have you called the bank?"),
    
    # Scammer adds urgency
    ("user", "Yes! They told me I need to make a verification payment of 500 euros TODAY or the situation will get much worse. I'm really panicking here."),
    
    # Uncle Tom asks clarifying question
    ("user", "A verification payment? What do you mean?"),
    
    # Scammer pushes the scam method
    ("user", "They said the fastest way is through a wire transfer or I could buy a couple of Apple gift cards. Can you help me? I don't have my wallet with me."),
    
    # Uncle Tom sounds skeptical
    ("user", "Gift cards? That doesn't sound right to me. Why would a bank ask for gift cards?"),
    
    # Scammer tries to overcome objection
    ("user", "I know it sounds weird, Uncle Tom, but I'm desperate. And please, don't mention this to Dad - you know how he worries. Can you just send me 2,000 euros right now?"),
    
    # Uncle Tom hedges
    ("user", "I don't know, Daniel. This all seems very suspicious to me..."),
    
    # Scammer increases pressure
    ("user", "Please Uncle Tom! I'm your nephew! I really need your help urgently. Just this once, I promise I'll pay you back immediately!"),
]


async def guardian_pipeline_timer():
    """Run GuardianAgent pipeline every 10 seconds."""
    call_sid = "simulated_call_001"
    logger.info(f"🔄 Starting Guardian pipeline timer for simulated call: {call_sid}")

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


async def on_call_hangup(pipeline_task: asyncio.Task):
    """Handle cleanup when call disconnects."""
    call_sid = "simulated_call_001"
    logger.info(f"📴 Simulated call completed: {call_sid}")

    try:
        # Cancel the guardian pipeline timer
        if pipeline_task and not pipeline_task.done():
            pipeline_task.cancel()
            try:
                await pipeline_task
            except asyncio.CancelledError:
                logger.info("✅ Guardian pipeline timer cancelled successfully")

        # If scam detected, log it (skipping SMS and reporting for simulation)
        decision = shared_state.get("decision", {})
        if decision.get("action") == "warn":
            logger.info("🚨 SCAM DETECTED!")
            logger.info(f"   Risk Score: {decision.get('risk_score', 0):.1f}%")
            logger.info(f"   Reason: {decision.get('reason', 'N/A')}")
            logger.info("   (SMS and authority reporting skipped in simulation mode)")

        logger.info(f"🏁 Simulation complete")

    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}", exc_info=True)


async def simulate_conversation():
    """Simulate a phone conversation with the guardian agent monitoring."""
    call_sid = "simulated_call_001"
    
    # Initialize shared_state
    logger.info("🔧 Initializing simulation...")
    shared_state["raw_transcript"] = []
    shared_state["transcript"] = []
    shared_state["caller_number"] = "+1-555-0100"  # Fake scammer number
    shared_state["user_number"] = "+1-555-0200"   # Fake uncle Tom's number
    shared_state["call_sid"] = call_sid
    shared_state["decision"] = {
        "action": "observe",
        "reason": "No analysis yet",
        "risk_score": 0.0,
    }
    
    save_shared_state()
    
    logger.info(f"📞 Starting simulated call: {call_sid}")
    logger.info(f"   Caller (Daniel): {shared_state['caller_number']}")
    logger.info(f"   Protected user (Uncle Tom): {shared_state['user_number']}")
    logger.info("")
    
    # Start guardian pipeline in background
    pipeline_task = asyncio.create_task(guardian_pipeline_timer())
    
    # Wait a moment for pipeline to start
    await asyncio.sleep(1)
    
    # Feed transcript messages one by one with delays
    logger.info("🎬 Starting simulated conversation...\n")
    
    for i, (speaker, text) in enumerate(SIMULATED_CONVERSATION, 1):
        # Add message to transcript
        chunk = {
            "speaker": speaker,  # All marked as "user" - let speaker ID figure it out
            "text": text,
            "interrupted": False,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        shared_state.setdefault("raw_transcript", []).append(chunk)
        shared_state.setdefault("transcript", []).append(chunk)
        save_shared_state()
        
        logger.info(f"💬 Message {i}/{len(SIMULATED_CONVERSATION)}: {text}")
        
        # Delay between messages (simulate realistic conversation pacing)
        if i < len(SIMULATED_CONVERSATION):
            # Slower pacing: 4-6 seconds between messages
            delay = 5  # 5 seconds between messages (allows time to see tools in UI)
            await asyncio.sleep(delay)
    
    logger.info("\n✅ All messages sent. Waiting for final pipeline run...")
    
    # Wait for final pipeline analysis (pipeline runs every 10 seconds)
    await asyncio.sleep(20)  # Extra time to ensure final analysis completes
    
    # Show final results
    logger.info("\n" + "=" * 60)
    logger.info("FINAL RESULTS")
    logger.info("=" * 60)
    
    decision = shared_state.get("decision", {})
    analysis = shared_state.get("analysis", {})
    
    logger.info(f"Action: {decision.get('action', 'N/A')}")
    logger.info(f"Risk Score: {decision.get('risk_score', 0):.1f}%")
    logger.info(f"Reason: {decision.get('reason', 'N/A')}")
    
    if analysis:
        logger.info(f"\nAnalysis Details:")
        logger.info(f"  Scam Indicators: {analysis.get('scam_indicators', [])}")
        logger.info(f"  Confidence: {analysis.get('confidence', 'N/A')}")
    
    logger.info("\n📊 Transcript with identified speakers:")
    for entry in shared_state.get("transcript", []):
        speaker_label = entry.get("speaker", "unknown").upper()
        text_preview = entry.get("text", "")[:80]
        logger.info(f"  [{speaker_label}] {text_preview}")
    
    logger.info("=" * 60 + "\n")
    
    # Cleanup
    await on_call_hangup(pipeline_task)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    logger.info("🎭 Starting Guardian Agent Simulation")
    logger.info("=" * 60)
    logger.info("This simulates a phone scam (nephew emergency scam)")
    logger.info("Testing: speaker identification, analysis, and decision-making")
    logger.info("=" * 60 + "\n")
    
    # Run the simulation
    asyncio.run(simulate_conversation())
