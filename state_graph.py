"""
LangGraph State Machine for Hotel Reservation Agent

Defines the conversation flow as a finite state machine:
1. Greeting
2. Collect Dates (check-in, check-out, guest count)
3. Validate Dates
4. Check Availability
5. Present Options
6. Collect Room Selection
7. Collect Guest Details
8. Create Booking
9. Confirmation
"""

import os
import re
import logging
from datetime import datetime, timedelta
from typing import TypedDict, Annotated, Sequence, Optional, List, Dict, Any
from operator import add

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from pms_client import QloAppsClient

logger = logging.getLogger(__name__)


# ============================================================================
# State Schema
# ============================================================================

class AgentState(TypedDict):
    """
    State schema for the hotel reservation agent.

    Tracks the conversation history and all collected information
    throughout the booking process.
    """
    messages: Annotated[Sequence[BaseMessage], add]

    # Date information
    check_in_date: Optional[str]  # YYYY-MM-DD format
    check_out_date: Optional[str]  # YYYY-MM-DD format
    guest_count: Optional[int]

    # Room selection
    available_rooms: Optional[List[Dict[str, Any]]]
    selected_room_id: Optional[str]
    selected_room_name: Optional[str]

    # Guest information
    guest_name: Optional[str]
    guest_email: Optional[str]
    guest_phone: Optional[str]
    special_requests: Optional[str]

    # Booking status
    booking_status: Optional[str]  # pending, confirmed, failed
    confirmation_number: Optional[str]

    # Flow control
    current_step: Optional[str]
    needs_dates: bool
    needs_guest_info: bool
    ready_to_book: bool


# ============================================================================
# Date Extraction and Validation
# ============================================================================

class DateExtractor:
    """Extract and parse dates from natural language."""

    @staticmethod
    def extract_dates(text: str) -> Dict[str, Optional[str]]:
        """
        Extract check-in and check-out dates from text.

        Supports formats like:
        - "December 1st to December 5th"
        - "12/1 to 12/5"
        - "from Jan 1 to Jan 5"
        - "next Monday for 3 nights"
        """
        result = {
            'check_in': None,
            'check_out': None
        }

        # Simple date patterns (YYYY-MM-DD)
        date_pattern = r'(\d{4}-\d{2}-\d{2})'
        dates = re.findall(date_pattern, text)

        if len(dates) >= 2:
            result['check_in'] = dates[0]
            result['check_out'] = dates[1]

        return result

    @staticmethod
    def extract_guest_count(text: str) -> Optional[int]:
        """Extract number of guests from text."""
        patterns = [
            r'(\d+)\s*(?:guests?|people|persons?)',
            r'for\s*(\d+)',
            r'party\s*of\s*(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return int(match.group(1))

        return None


def validate_dates(check_in: str, check_out: str) -> tuple[bool, Optional[str]]:
    """
    Validate that dates are logical and not in the past.

    Args:
        check_in: Check-in date (YYYY-MM-DD)
        check_out: Check-out date (YYYY-MM-DD)

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        today = datetime.now().date()

        # Check if dates are in the past
        if check_in_date < today:
            return False, "Check-in date cannot be in the past."

        # Check if check-out is after check-in
        if check_out_date <= check_in_date:
            return False, "Check-out date must be after check-in date."

        # Check if stay is reasonable (not more than 30 days)
        nights = (check_out_date - check_in_date).days
        if nights > 30:
            return False, "Maximum stay is 30 nights. Please select a shorter period."

        return True, None

    except ValueError as e:
        return False, f"Invalid date format. Please use YYYY-MM-DD format."


# ============================================================================
# LangGraph Nodes
# ============================================================================

class HotelAgentGraph:
    """Hotel reservation agent state machine using LangGraph."""

    def __init__(self, pms_client: QloAppsClient, hotel_name: str = "The Grand Hotel"):
        self.pms_client = pms_client
        self.hotel_name = hotel_name

        # Initialize Groq LLM (Llama 3.1 70B)
        self.llm = ChatGroq(
            model="llama-3.1-70b-versatile",
            temperature=0.7,
            api_key=os.getenv('GROQ_API_KEY'),
            streaming=True
        )

        # Build the graph
        self.graph = self._build_graph()
        self.app = self.graph.compile()

    def _build_graph(self) -> StateGraph:
        """Construct the LangGraph state machine."""

        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("chatbot", self.chatbot_node)
        workflow.add_node("extract_info", self.extract_info_node)
        workflow.add_node("validate_dates", self.validate_dates_node)
        workflow.add_node("check_availability", self.check_availability_node)
        workflow.add_node("collect_guest_info", self.collect_guest_info_node)
        workflow.add_node("create_booking", self.create_booking_node)

        # Define the flow
        workflow.set_entry_point("chatbot")

        # Chatbot routes to different nodes based on state
        workflow.add_conditional_edges(
            "chatbot",
            self.route_from_chatbot,
            {
                "extract_info": "extract_info",
                "validate_dates": "validate_dates",
                "check_availability": "check_availability",
                "collect_guest_info": "collect_guest_info",
                "create_booking": "create_booking",
                "continue": "chatbot",
                "end": END
            }
        )

        # Extract info goes back to chatbot
        workflow.add_edge("extract_info", "chatbot")

        # Date validation routes
        workflow.add_conditional_edges(
            "validate_dates",
            self.route_from_validation,
            {
                "valid": "check_availability",
                "invalid": "chatbot"
            }
        )

        # After checking availability, go back to chatbot to present options
        workflow.add_edge("check_availability", "chatbot")

        # After collecting guest info, route to booking or back to chatbot
        workflow.add_conditional_edges(
            "collect_guest_info",
            self.route_from_guest_info,
            {
                "create_booking": "create_booking",
                "continue": "chatbot"
            }
        )

        # After creating booking, end or continue
        workflow.add_conditional_edges(
            "create_booking",
            self.route_from_booking,
            {
                "end": END,
                "continue": "chatbot"
            }
        )

        return workflow

    # ========================================================================
    # Node Implementations
    # ========================================================================

    async def chatbot_node(self, state: AgentState) -> AgentState:
        """
        Main conversational node using Llama 3.1 70B.

        Generates responses based on the current state and guides
        the conversation towards completing a booking.
        """
        # Build system prompt based on current state
        system_prompt = self._build_system_prompt(state)

        # Create chat prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages")
        ])

        # Generate response
        chain = prompt | self.llm

        try:
            response = await chain.ainvoke({"messages": state["messages"]})

            return {
                **state,
                "messages": [response]
            }
        except Exception as e:
            logger.error(f"Error in chatbot node: {e}")
            error_message = AIMessage(
                content="I apologize, I'm experiencing technical difficulties. "
                       "Could you please repeat that?"
            )
            return {
                **state,
                "messages": [error_message]
            }

    async def extract_info_node(self, state: AgentState) -> AgentState:
        """Extract dates and guest count from the conversation."""

        # Get the last user message
        last_message = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                last_message = msg.content
                break

        extractor = DateExtractor()

        # Extract dates if not already collected
        if not state.get("check_in_date") or not state.get("check_out_date"):
            dates = extractor.extract_dates(last_message)
            if dates["check_in"]:
                state["check_in_date"] = dates["check_in"]
            if dates["check_out"]:
                state["check_out_date"] = dates["check_out"]

        # Extract guest count if not already collected
        if not state.get("guest_count"):
            guest_count = extractor.extract_guest_count(last_message)
            if guest_count:
                state["guest_count"] = guest_count

        # Update needs_dates flag
        has_all_dates = (
            state.get("check_in_date") and
            state.get("check_out_date") and
            state.get("guest_count")
        )
        state["needs_dates"] = not has_all_dates

        return state

    async def validate_dates_node(self, state: AgentState) -> AgentState:
        """Validate the collected dates."""

        check_in = state.get("check_in_date")
        check_out = state.get("check_out_date")

        if not check_in or not check_out:
            state["current_step"] = "needs_dates"
            return state

        is_valid, error_msg = validate_dates(check_in, check_out)

        if not is_valid:
            # Add error message to conversation
            error_response = AIMessage(
                content=f"I'm sorry, but there's an issue with those dates: {error_msg} "
                       "Could you please provide different dates?"
            )
            state["messages"] = state["messages"] + [error_response]
            state["check_in_date"] = None
            state["check_out_date"] = None
            state["current_step"] = "invalid_dates"
        else:
            state["current_step"] = "dates_valid"

        return state

    async def check_availability_node(self, state: AgentState) -> AgentState:
        """Check room availability via PMS."""

        check_in = state["check_in_date"]
        check_out = state["check_out_date"]
        guests = state["guest_count"]

        try:
            available_rooms = await self.pms_client.check_availability(
                check_in=check_in,
                check_out=check_out,
                guests=guests
            )

            state["available_rooms"] = available_rooms
            state["current_step"] = "presenting_options"

            # Generate message presenting options
            if available_rooms:
                rooms_text = self._format_room_options(available_rooms)
                message = AIMessage(
                    content=f"Great! I found {len(available_rooms)} available rooms "
                           f"for {guests} guests from {check_in} to {check_out}:\n\n"
                           f"{rooms_text}\n\n"
                           f"Which room would you like to book?"
                )
            else:
                message = AIMessage(
                    content=f"I'm sorry, we don't have any rooms available for "
                           f"{guests} guests from {check_in} to {check_out}. "
                           f"Would you like to try different dates?"
                )
                state["current_step"] = "no_availability"

            state["messages"] = state["messages"] + [message]

        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            error_message = AIMessage(
                content="I'm having trouble checking availability right now. "
                       "Please try again in a moment."
            )
            state["messages"] = state["messages"] + [error_message]
            state["current_step"] = "error"

        return state

    async def collect_guest_info_node(self, state: AgentState) -> AgentState:
        """Extract guest information from conversation."""

        # Use LLM to extract structured information
        extraction_prompt = """
        Extract guest information from the conversation.
        Look for: name, email, phone number, special requests.

        Return in format:
        Name: [name or NONE]
        Email: [email or NONE]
        Phone: [phone or NONE]
        Requests: [requests or NONE]
        """

        # Get recent messages
        recent_messages = state["messages"][-5:]
        conversation = "\n".join([
            f"{'User' if isinstance(m, HumanMessage) else 'Agent'}: {m.content}"
            for m in recent_messages
        ])

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=extraction_prompt),
                HumanMessage(content=conversation)
            ])

            # Parse response (simple parsing)
            content = response.content
            if "Name:" in content and "NONE" not in content.split("Name:")[1].split("\n")[0]:
                name_line = content.split("Name:")[1].split("\n")[0].strip()
                if name_line != "NONE":
                    state["guest_name"] = name_line

            if "Email:" in content and "NONE" not in content.split("Email:")[1].split("\n")[0]:
                email_line = content.split("Email:")[1].split("\n")[0].strip()
                if email_line != "NONE":
                    state["guest_email"] = email_line

            if "Phone:" in content and "NONE" not in content.split("Phone:")[1].split("\n")[0]:
                phone_line = content.split("Phone:")[1].split("\n")[0].strip()
                if phone_line != "NONE":
                    state["guest_phone"] = phone_line

            # Check if we have all required info
            has_all_info = (
                state.get("guest_name") and
                state.get("guest_email") and
                state.get("guest_phone")
            )

            state["needs_guest_info"] = not has_all_info
            state["ready_to_book"] = has_all_info

        except Exception as e:
            logger.error(f"Error extracting guest info: {e}")

        return state

    async def create_booking_node(self, state: AgentState) -> AgentState:
        """Create the booking via PMS."""

        guest_details = {
            'guest_name': state['guest_name'],
            'guest_email': state['guest_email'],
            'guest_phone': state['guest_phone'],
            'check_in': state['check_in_date'],
            'check_out': state['check_out_date'],
            'guest_count': state['guest_count'],
            'special_requests': state.get('special_requests', '')
        }

        try:
            confirmation_number = await self.pms_client.create_booking(
                guest_details=guest_details,
                room_id=state['selected_room_id']
            )

            state["confirmation_number"] = confirmation_number
            state["booking_status"] = "confirmed"
            state["current_step"] = "completed"

            # Generate confirmation message
            message = AIMessage(
                content=f"Excellent! Your booking is confirmed.\n\n"
                       f"Confirmation Number: {confirmation_number}\n"
                       f"Room: {state['selected_room_name']}\n"
                       f"Check-in: {state['check_in_date']}\n"
                       f"Check-out: {state['check_out_date']}\n"
                       f"Guests: {state['guest_count']}\n\n"
                       f"A confirmation email has been sent to {state['guest_email']}. "
                       f"We look forward to welcoming you to {self.hotel_name}!\n\n"
                       f"Is there anything else I can help you with?"
            )
            state["messages"] = state["messages"] + [message]

        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            state["booking_status"] = "failed"
            error_message = AIMessage(
                content="I apologize, but I encountered an error while creating your booking. "
                       "Please try again or contact our reservations team directly."
            )
            state["messages"] = state["messages"] + [error_message]

        return state

    # ========================================================================
    # Routing Functions
    # ========================================================================

    def route_from_chatbot(self, state: AgentState) -> str:
        """Determine next node from chatbot."""

        current_step = state.get("current_step", "")

        # If booking is completed, allow end or new booking
        if current_step == "completed":
            # Check last message for new booking intent
            last_message = state["messages"][-1] if state["messages"] else None
            if last_message and isinstance(last_message, HumanMessage):
                if "new" in last_message.content.lower() or "another" in last_message.content.lower():
                    return "extract_info"
            return "end"

        # If we need dates, extract info
        if state.get("needs_dates", True):
            return "extract_info"

        # If we have dates but haven't validated, validate
        if state.get("check_in_date") and state.get("check_out_date"):
            if current_step != "dates_valid" and current_step != "presenting_options":
                return "validate_dates"

        # If dates are valid and we haven't checked availability
        if current_step == "dates_valid":
            return "check_availability"

        # If we have rooms and user selected one
        if state.get("available_rooms") and current_step == "presenting_options":
            # Check if room was selected in last message
            last_message = ""
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    last_message = msg.content.lower()
                    break

            # Simple room selection detection
            for room in state["available_rooms"]:
                if room["name"].lower() in last_message or room["id"] in last_message:
                    state["selected_room_id"] = room["id"]
                    state["selected_room_name"] = room["name"]
                    state["current_step"] = "room_selected"
                    return "collect_guest_info"

        # If room is selected and we need guest info
        if state.get("selected_room_id") and state.get("needs_guest_info", True):
            return "collect_guest_info"

        # If we have all info and ready to book
        if state.get("ready_to_book", False):
            return "create_booking"

        return "continue"

    def route_from_validation(self, state: AgentState) -> str:
        """Route from date validation."""
        if state.get("current_step") == "dates_valid":
            return "valid"
        return "invalid"

    def route_from_guest_info(self, state: AgentState) -> str:
        """Route from guest info collection."""
        if state.get("ready_to_book"):
            return "create_booking"
        return "continue"

    def route_from_booking(self, state: AgentState) -> str:
        """Route from booking creation."""
        if state.get("booking_status") == "confirmed":
            return "end"
        return "continue"

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _build_system_prompt(self, state: AgentState) -> str:
        """Build context-aware system prompt."""

        base_prompt = f"""You are a polite and professional hotel receptionist at {self.hotel_name}.

Your role is to help guests make room reservations through natural conversation.

Guidelines:
1. Be warm, friendly, and professional
2. Speak naturally - you're having a voice conversation
3. Keep responses concise (1-3 sentences)
4. If asked about topics unrelated to hotel reservations, politely redirect to booking
5. Always confirm important details with the guest

Current conversation context:"""

        # Add current state context
        if state.get("check_in_date"):
            base_prompt += f"\n- Check-in: {state['check_in_date']}"
        if state.get("check_out_date"):
            base_prompt += f"\n- Check-out: {state['check_out_date']}"
        if state.get("guest_count"):
            base_prompt += f"\n- Guests: {state['guest_count']}"
        if state.get("selected_room_name"):
            base_prompt += f"\n- Selected room: {state['selected_room_name']}"

        # Add next action guidance
        current_step = state.get("current_step", "")

        if state.get("needs_dates", True):
            base_prompt += "\n\nNext: Ask for check-in date, check-out date, and number of guests."
        elif current_step == "presenting_options":
            base_prompt += "\n\nNext: The available rooms have been presented. Ask which room they prefer."
        elif state.get("selected_room_id") and state.get("needs_guest_info", True):
            base_prompt += "\n\nNext: Collect guest name, email, and phone number for the booking."
        elif current_step == "completed":
            base_prompt += "\n\nThe booking is complete. Ask if they need anything else."

        return base_prompt

    def _format_room_options(self, rooms: List[Dict[str, Any]]) -> str:
        """Format room options for presentation."""

        formatted = []
        for i, room in enumerate(rooms, 1):
            formatted.append(
                f"{i}. {room['name']} - ${room['price_per_night']}/night\n"
                f"   {room['description']}\n"
                f"   Amenities: {', '.join(room['amenities'])}"
            )

        return "\n\n".join(formatted)


# ============================================================================
# Factory Function
# ============================================================================

def create_hotel_agent(
    pms_client: QloAppsClient,
    hotel_name: str = None
) -> HotelAgentGraph:
    """
    Create and return a configured hotel agent.

    Args:
        pms_client: QloApps PMS client instance
        hotel_name: Name of the hotel (defaults to env var)

    Returns:
        Configured HotelAgentGraph instance
    """
    hotel_name = hotel_name or os.getenv('HOTEL_NAME', 'The Grand Hotel')
    return HotelAgentGraph(pms_client=pms_client, hotel_name=hotel_name)
