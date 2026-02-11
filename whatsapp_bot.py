"""
WhatsApp Bot Handler for Hotel Reservation Agent

This module provides WhatsApp integration using Twilio's WhatsApp API.
It handles incoming messages, manages conversation state, and integrates
with the LangGraph state machine.
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional
from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import redis
import json
from dotenv import load_dotenv

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

# Initialize Flask app
app = Flask(__name__)

# Initialize Twilio client
twilio_client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)

# Initialize Redis for session management
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0)),
    decode_responses=True
)

# Initialize PMS client
pms_client = QloAppsClient(
    base_url=os.getenv('QLOAPPS_BASE_URL'),
    api_key=os.getenv('QLOAPPS_API_KEY'),
    mock_mode=os.getenv('PMS_MOCK_MODE', 'true').lower() == 'true'
)

# Initialize hotel agent
hotel_agent = create_hotel_agent(
    pms_client=pms_client,
    hotel_name=os.getenv('HOTEL_NAME', 'The Grand Hotel')
)


# ============================================================================
# Session Management
# ============================================================================

class SessionManager:
    """Manage user sessions in Redis."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.session_ttl = int(os.getenv('SESSION_TTL_SECONDS', 3600))  # 1 hour default

    def get_session(self, user_id: str) -> Optional[AgentState]:
        """Retrieve user session from Redis."""
        try:
            session_key = f"whatsapp_session:{user_id}"
            session_data = self.redis.get(session_key)

            if session_data:
                data = json.loads(session_data)
                # Convert message dictionaries back to message objects
                messages = []
                for msg in data.get('messages', []):
                    if msg['type'] == 'human':
                        messages.append(HumanMessage(content=msg['content']))
                    elif msg['type'] == 'ai':
                        messages.append(AIMessage(content=msg['content']))

                data['messages'] = messages
                return data
            else:
                # Return new session state
                return self._create_new_session()

        except Exception as e:
            logger.error(f"Error retrieving session for {user_id}: {e}")
            return self._create_new_session()

    def save_session(self, user_id: str, state: AgentState):
        """Save user session to Redis."""
        try:
            session_key = f"whatsapp_session:{user_id}"

            # Convert message objects to dictionaries for JSON serialization
            serializable_state = {**state}
            serializable_state['messages'] = [
                {
                    'type': 'human' if isinstance(msg, HumanMessage) else 'ai',
                    'content': msg.content
                }
                for msg in state['messages']
            ]

            # Save to Redis with TTL
            self.redis.setex(
                session_key,
                self.session_ttl,
                json.dumps(serializable_state)
            )

        except Exception as e:
            logger.error(f"Error saving session for {user_id}: {e}")

    def clear_session(self, user_id: str):
        """Clear user session."""
        try:
            session_key = f"whatsapp_session:{user_id}"
            self.redis.delete(session_key)
            logger.info(f"Session cleared for {user_id}")
        except Exception as e:
            logger.error(f"Error clearing session for {user_id}: {e}")

    def _create_new_session(self) -> AgentState:
        """Create a new agent state."""
        return {
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


# Initialize session manager
session_manager = SessionManager(redis_client)


# ============================================================================
# Message Processing
# ============================================================================

async def process_message(user_id: str, user_message: str, user_phone: str) -> str:
    """
    Process incoming WhatsApp message through the state machine.

    Args:
        user_id: Unique user identifier
        user_message: User's message text
        user_phone: User's phone number

    Returns:
        Bot's response message
    """
    try:
        # Get or create session
        state = session_manager.get_session(user_id)

        # Check for special commands
        message_lower = user_message.lower().strip()

        if message_lower in ['reset', 'restart', 'start over', 'new booking']:
            session_manager.clear_session(user_id)
            state = session_manager.get_session(user_id)
            return (
                f"Welcome to {os.getenv('HOTEL_NAME', 'The Grand Hotel')}! 🏨\n\n"
                f"I'm here to help you make a reservation.\n\n"
                f"To get started, please let me know:\n"
                f"• Check-in date\n"
                f"• Check-out date\n"
                f"• Number of guests\n\n"
                f"Example: \"I need a room from 2024-12-15 to 2024-12-20 for 2 guests\""
            )

        if message_lower in ['help', 'menu']:
            return (
                f"📋 *{os.getenv('HOTEL_NAME', 'The Grand Hotel')} - Help Menu*\n\n"
                f"*Commands:*\n"
                f"• Type your booking request naturally\n"
                f"• 'reset' - Start a new booking\n"
                f"• 'help' - Show this menu\n"
                f"• 'status' - Check current booking status\n\n"
                f"*Booking Process:*\n"
                f"1️⃣ Provide dates and guest count\n"
                f"2️⃣ Select a room from available options\n"
                f"3️⃣ Provide guest details\n"
                f"4️⃣ Receive confirmation\n\n"
                f"Need assistance? Just ask!"
            )

        if message_lower == 'status':
            status_msg = self._get_booking_status(state)
            return status_msg

        # Store user's phone if not already stored
        if not state.get('guest_phone'):
            state['guest_phone'] = user_phone

        # Add user message to state
        state['messages'] = state['messages'] + [HumanMessage(content=user_message)]

        # Run through state machine
        result = await hotel_agent.app.ainvoke(state)

        # Update session
        session_manager.save_session(user_id, result)

        # Extract the last AI message
        last_ai_message = ""
        for msg in reversed(result['messages']):
            if isinstance(msg, AIMessage):
                last_ai_message = msg.content
                break

        if not last_ai_message:
            last_ai_message = "I'm here to help! Could you please tell me your check-in date?"

        # Format message for WhatsApp
        formatted_message = format_whatsapp_message(last_ai_message, result)

        return formatted_message

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return (
            "I apologize, but I encountered an error processing your request. "
            "Please try again or type 'reset' to start over."
        )


def _get_booking_status(state: AgentState) -> str:
    """Get current booking status."""
    status_parts = [f"📊 *Booking Status*\n"]

    if state.get('check_in_date') and state.get('check_out_date'):
        status_parts.append(
            f"✅ Dates: {state['check_in_date']} to {state['check_out_date']}"
        )
    else:
        status_parts.append("⏳ Dates: Not provided")

    if state.get('guest_count'):
        status_parts.append(f"✅ Guests: {state['guest_count']}")
    else:
        status_parts.append("⏳ Guests: Not provided")

    if state.get('selected_room_name'):
        status_parts.append(f"✅ Room: {state['selected_room_name']}")
    else:
        status_parts.append("⏳ Room: Not selected")

    if state.get('guest_name'):
        status_parts.append(f"✅ Guest Name: {state['guest_name']}")
    else:
        status_parts.append("⏳ Guest Name: Not provided")

    if state.get('booking_status') == 'confirmed':
        status_parts.append(
            f"\n✅ *Booking Confirmed!*\n"
            f"Confirmation: {state.get('confirmation_number')}"
        )

    return "\n".join(status_parts)


def format_whatsapp_message(message: str, state: AgentState) -> str:
    """
    Format message for better WhatsApp display.

    Args:
        message: Raw message from LLM
        state: Current agent state

    Returns:
        Formatted message with WhatsApp markdown
    """
    # Add formatting for better readability
    formatted = message

    # Add emoji indicators for important steps
    if state.get('current_step') == 'presenting_options':
        formatted = "🏨 " + formatted

    if state.get('booking_status') == 'confirmed':
        formatted = "✅ " + formatted

    # Format room lists better
    if state.get('available_rooms') and len(state['available_rooms']) > 0:
        lines = formatted.split('\n')
        formatted_lines = []
        for line in lines:
            # Detect room options and add better formatting
            if any(room['name'] in line for room in state['available_rooms']):
                line = "🛏️ " + line
            formatted_lines.append(line)
        formatted = '\n'.join(formatted_lines)

    return formatted


# ============================================================================
# Webhook Endpoints
# ============================================================================

@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """
    Handle incoming WhatsApp messages from Twilio.

    This endpoint receives messages via Twilio's WhatsApp API.
    """
    try:
        # Get message details
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')
        to_number = request.values.get('To', '')

        # Extract user ID from phone number
        user_id = from_number.replace('whatsapp:', '')

        logger.info(f"Received message from {user_id}: {incoming_msg}")

        # Process message asynchronously
        response_text = asyncio.run(
            process_message(user_id, incoming_msg, from_number)
        )

        # Send response via Twilio
        resp = MessagingResponse()
        msg = resp.message()
        msg.body(response_text)

        logger.info(f"Sent response to {user_id}: {response_text[:100]}...")

        return str(resp)

    except Exception as e:
        logger.error(f"Error in webhook: {e}", exc_info=True)

        resp = MessagingResponse()
        resp.message(
            "Sorry, I encountered an error. Please try again later or contact support."
        )
        return str(resp)


@app.route('/webhook/status', methods=['POST'])
def status_webhook():
    """Handle message status updates from Twilio."""
    try:
        message_sid = request.values.get('MessageSid')
        message_status = request.values.get('MessageStatus')

        logger.info(f"Message {message_sid} status: {message_status}")

        return jsonify({'status': 'ok'})

    except Exception as e:
        logger.error(f"Error in status webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Check Redis connection
        redis_client.ping()

        return jsonify({
            'status': 'healthy',
            'service': 'whatsapp-hotel-bot',
            'timestamp': datetime.utcnow().isoformat(),
            'redis': 'connected',
            'hotel': os.getenv('HOTEL_NAME', 'The Grand Hotel')
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503


@app.route('/api/send-message', methods=['POST'])
def send_message_api():
    """
    API endpoint to send messages to users.

    Useful for notifications, confirmations, etc.
    """
    try:
        data = request.get_json()
        to_number = data.get('to')
        message = data.get('message')

        if not to_number or not message:
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: to, message'
            }), 400

        # Ensure WhatsApp format
        if not to_number.startswith('whatsapp:'):
            to_number = f"whatsapp:{to_number}"

        # Send via Twilio
        twilio_message = twilio_client.messages.create(
            body=message,
            from_=os.getenv('TWILIO_WHATSAPP_NUMBER'),
            to=to_number
        )

        return jsonify({
            'status': 'success',
            'message_sid': twilio_message.sid
        })

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/clear-session/<user_id>', methods=['DELETE'])
def clear_user_session(user_id: str):
    """Clear a user's session (admin endpoint)."""
    try:
        session_manager.clear_session(user_id)
        return jsonify({
            'status': 'success',
            'message': f'Session cleared for {user_id}'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================================
# Main
# ============================================================================

def main():
    """Run the Flask app."""

    # Validate environment variables
    required_vars = [
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'TWILIO_WHATSAPP_NUMBER',
        'GROQ_API_KEY'
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file")
        return

    logger.info("Starting WhatsApp Hotel Bot")
    logger.info(f"Hotel: {os.getenv('HOTEL_NAME', 'The Grand Hotel')}")
    logger.info(f"WhatsApp Number: {os.getenv('TWILIO_WHATSAPP_NUMBER')}")

    # Run Flask app
    port = int(os.getenv('WHATSAPP_BOT_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )


if __name__ == "__main__":
    main()
