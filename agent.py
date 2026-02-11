"""
Voice-Governed Hotel Reservation Agent

Main entry point that integrates:
- LiveKit for WebRTC/Voice connectivity
- Deepgram for Speech-to-Text
- Cartesia for Text-to-Speech
- Groq (Llama 3.1 70B) for LLM inference
- LangGraph for conversation state management
- QloApps for PMS integration
"""

import asyncio
import logging
import os
from typing import Optional
from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, cartesia, silero

from langchain_core.messages import HumanMessage, AIMessage

from pms_client import QloAppsClient
from state_graph import create_hotel_agent, AgentState

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Agent Configuration
# ============================================================================

class HotelVoiceAgent:
    """Voice agent for hotel reservations using LiveKit."""

    def __init__(self, ctx: JobContext):
        self.ctx = ctx
        self.chat_context = None

        # Initialize PMS client
        self.pms_client = QloAppsClient(
            base_url=os.getenv('QLOAPPS_BASE_URL'),
            api_key=os.getenv('QLOAPPS_API_KEY'),
            mock_mode=True  # Set to False for production
        )

        # Initialize LangGraph state machine
        self.hotel_agent = create_hotel_agent(
            pms_client=self.pms_client,
            hotel_name=os.getenv('HOTEL_NAME', 'The Grand Hotel')
        )

        # Initialize agent state
        self.agent_state: AgentState = {
            'messages': [],
            'check_in_date': None,
            'check_out_date': None,
            'guest_count': None,
            'available_rooms': None,
            'selected_room_id': None,
            'selected_room_name': None,
            'guest_name': None,
            'guest_email': None,
            'guest_phone': None,
            'special_requests': None,
            'booking_status': None,
            'confirmation_number': None,
            'current_step': None,
            'needs_dates': True,
            'needs_guest_info': True,
            'ready_to_book': False
        }

        # Track if initial greeting has been sent
        self.initial_greeting_sent = False

    async def run(self):
        """Main entry point for the voice agent."""

        logger.info(f"Starting hotel voice agent for room: {self.ctx.room.name}")

        # Check if this is a phone/SIP call
        is_phone_call = self.ctx.room.name.startswith("call-")

        # Connect to room
        await self.ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

        # Wait for participant to join
        participant = await self.ctx.wait_for_participant()
        logger.info(f"Participant joined: {participant.identity}")

        # Create the voice pipeline agent
        agent = VoicePipelineAgent(
            vad=silero.VAD.load(
                min_speech_duration=0.1,
                min_silence_duration=0.5,
                activation_threshold=float(os.getenv('VAD_THRESHOLD', '0.5')),
            ),
            stt=deepgram.STT(
                api_key=os.getenv('DEEPGRAM_API_KEY'),
                model="nova-2-general",
                language="en-US",
                smart_format=True,
                interim_results=False,
            ),
            llm=self._create_llm_adapter(),
            tts=cartesia.TTS(
                api_key=os.getenv('CARTESIA_API_KEY'),
                voice="79a125e8-cd45-4c13-8a67-188112f4dd22",  # Professional female voice
                model="sonic-english",
                encoding="pcm_s16le",
                sample_rate=24000,
            ),
            chat_ctx=self.chat_context,
        )

        # Configure agent for interruptions (barge-in)
        agent.allow_interruptions = os.getenv('ENABLE_INTERRUPTIONS', 'true').lower() == 'true'

        # Start the agent
        agent.start(self.ctx.room, participant)

        # Send initial greeting for phone calls
        if is_phone_call and not self.initial_greeting_sent:
            await self._send_initial_greeting(agent)
            self.initial_greeting_sent = True

        # Set up event handlers
        @agent.on("user_speech_committed")
        def on_user_speech(msg: str):
            """Handle user speech input."""
            logger.info(f"User said: {msg}")
            asyncio.create_task(self._handle_user_input(msg, agent))

        @agent.on("agent_speech_committed")
        def on_agent_speech(msg: str):
            """Handle agent speech output."""
            logger.info(f"Agent said: {msg}")

        @agent.on("agent_started_speaking")
        def on_started_speaking():
            logger.debug("Agent started speaking")

        @agent.on("agent_stopped_speaking")
        def on_stopped_speaking():
            logger.debug("Agent stopped speaking")

        # Keep the agent running
        await agent.aclose()

    async def _send_initial_greeting(self, agent: VoicePipelineAgent):
        """Send initial greeting for phone calls."""

        greeting = (
            f"Hello! Thank you for calling {os.getenv('HOTEL_NAME', 'The Grand Hotel')}. "
            f"I'm your virtual assistant. I'm here to help you make a reservation. "
            f"When would you like to check in?"
        )

        logger.info(f"Sending initial greeting: {greeting}")

        # Add to state
        greeting_msg = AIMessage(content=greeting)
        self.agent_state['messages'] = [greeting_msg]

        # Speak the greeting
        await agent.say(greeting, allow_interruptions=True)

    async def _handle_user_input(self, user_input: str, agent: VoicePipelineAgent):
        """
        Process user input through the LangGraph state machine
        and generate appropriate response.
        """

        try:
            # Add user message to state
            self.agent_state['messages'] = self.agent_state['messages'] + [
                HumanMessage(content=user_input)
            ]

            # Run the state graph
            result = await self.hotel_agent.app.ainvoke(self.agent_state)

            # Update state
            self.agent_state = result

            # Get the last AI message
            last_ai_message = None
            for msg in reversed(result['messages']):
                if isinstance(msg, AIMessage):
                    last_ai_message = msg.content
                    break

            # Speak the response if we have one
            if last_ai_message:
                # Stream to TTS for lower latency
                await agent.say(last_ai_message, allow_interruptions=True)

        except Exception as e:
            logger.error(f"Error handling user input: {e}", exc_info=True)

            # Send error response
            error_msg = (
                "I apologize, I'm having trouble processing that. "
                "Could you please repeat your request?"
            )
            await agent.say(error_msg, allow_interruptions=True)

    def _create_llm_adapter(self) -> llm.LLM:
        """
        Create an LLM adapter for the voice pipeline.

        This adapter wraps our LangGraph-based agent and makes it
        compatible with LiveKit's VoicePipelineAgent.
        """

        class LangGraphLLMAdapter(llm.LLM):
            """Adapter to use LangGraph with LiveKit's voice pipeline."""

            def __init__(self, parent: 'HotelVoiceAgent'):
                super().__init__()
                self.parent = parent

            async def chat(
                self,
                *,
                chat_ctx: llm.ChatContext,
                fnc_ctx: Optional[llm.FunctionContext] = None,
                temperature: Optional[float] = None,
                n: int = 1,
            ) -> llm.ChatResponse:
                """
                Process chat through our LangGraph state machine.
                """

                # Get the last user message
                user_message = None
                for msg in reversed(chat_ctx.messages):
                    if msg.role == "user":
                        user_message = msg.content
                        break

                if not user_message:
                    return llm.ChatResponse(
                        choices=[
                            llm.Choice(
                                delta=llm.ChatChunk(
                                    content="How can I help you today?",
                                    role="assistant"
                                )
                            )
                        ]
                    )

                try:
                    # Add to state
                    self.parent.agent_state['messages'] = (
                        self.parent.agent_state['messages'] +
                        [HumanMessage(content=user_message)]
                    )

                    # Run state graph
                    result = await self.parent.hotel_agent.app.ainvoke(
                        self.parent.agent_state
                    )

                    # Update state
                    self.parent.agent_state = result

                    # Get response
                    last_ai_message = ""
                    for msg in reversed(result['messages']):
                        if isinstance(msg, AIMessage):
                            last_ai_message = msg.content
                            break

                    return llm.ChatResponse(
                        choices=[
                            llm.Choice(
                                delta=llm.ChatChunk(
                                    content=last_ai_message,
                                    role="assistant"
                                )
                            )
                        ]
                    )

                except Exception as e:
                    logger.error(f"Error in LLM adapter: {e}", exc_info=True)
                    return llm.ChatResponse(
                        choices=[
                            llm.Choice(
                                delta=llm.ChatChunk(
                                    content="I apologize, I encountered an error. "
                                           "Could you please try again?",
                                    role="assistant"
                                )
                            )
                        ]
                    )

        return LangGraphLLMAdapter(self)


# ============================================================================
# LiveKit Worker Entry Point
# ============================================================================

async def entrypoint(ctx: JobContext):
    """
    LiveKit job entry point.

    This function is called for each new room/session.
    """

    logger.info(f"Entrypoint called for room: {ctx.room.name}")

    # Create and run the agent
    agent = HotelVoiceAgent(ctx)
    await agent.run()


# ============================================================================
# Main
# ============================================================================

def main():
    """Main entry point for the worker."""

    # Validate required environment variables
    required_vars = [
        'LIVEKIT_URL',
        'LIVEKIT_API_KEY',
        'LIVEKIT_API_SECRET',
        'DEEPGRAM_API_KEY',
        'CARTESIA_API_KEY',
        'GROQ_API_KEY'
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file")
        return

    logger.info("Starting Hotel Voice Agent Worker")
    logger.info(f"Hotel: {os.getenv('HOTEL_NAME', 'The Grand Hotel')}")
    logger.info(f"LiveKit URL: {os.getenv('LIVEKIT_URL')}")

    # Run the LiveKit worker
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            api_key=os.getenv('LIVEKIT_API_KEY'),
            api_secret=os.getenv('LIVEKIT_API_SECRET'),
            ws_url=os.getenv('LIVEKIT_URL'),
        )
    )


if __name__ == "__main__":
    main()
