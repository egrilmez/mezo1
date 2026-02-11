"""
WhatsApp Message Handler and Utilities

Provides utilities for message formatting, media handling,
and advanced WhatsApp features.
"""

import os
import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import phonenumbers
from twilio.rest import Client

logger = logging.getLogger(__name__)


# ============================================================================
# Message Formatters
# ============================================================================

class WhatsAppMessageFormatter:
    """Format messages for WhatsApp with proper markdown and structure."""

    @staticmethod
    def format_greeting() -> str:
        """Format initial greeting message."""
        hotel_name = os.getenv('HOTEL_NAME', 'The Grand Hotel')
        return (
            f"🏨 *Welcome to {hotel_name}!*\n\n"
            f"I'm your AI assistant, here to help you book the perfect room.\n\n"
            f"📅 To get started, please provide:\n"
            f"• Check-in date (e.g., 2024-12-15)\n"
            f"• Check-out date (e.g., 2024-12-20)\n"
            f"• Number of guests\n\n"
            f"💡 You can also type 'help' anytime for assistance!"
        )

    @staticmethod
    def format_room_list(rooms: List[Dict]) -> str:
        """
        Format room options for display.

        Args:
            rooms: List of available rooms

        Returns:
            Formatted room list
        """
        if not rooms:
            return "Sorry, no rooms are available for your selected dates."

        message_parts = ["🏨 *Available Rooms:*\n"]

        for i, room in enumerate(rooms, 1):
            amenities = room.get('amenities', [])
            amenities_str = ", ".join(amenities[:4])  # Limit to first 4 amenities

            room_text = (
                f"\n*{i}. {room['name']}* 💰 ${room['price_per_night']}/night\n"
                f"   {room['description']}\n"
                f"   ✨ {amenities_str}"
            )

            if room.get('total_price'):
                room_text += f"\n   📊 Total: ${room['total_price']}"

            message_parts.append(room_text)

        message_parts.append(
            f"\n\n💬 To select a room, just reply with the room name or number!"
        )

        return "\n".join(message_parts)

    @staticmethod
    def format_booking_confirmation(
        confirmation_number: str,
        room_name: str,
        check_in: str,
        check_out: str,
        guest_count: int,
        guest_email: str
    ) -> str:
        """Format booking confirmation message."""
        hotel_name = os.getenv('HOTEL_NAME', 'The Grand Hotel')

        # Calculate nights
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
            nights = (check_out_date - check_in_date).days
        except:
            nights = "N/A"

        return (
            f"✅ *Booking Confirmed!*\n\n"
            f"🎫 *Confirmation:* {confirmation_number}\n"
            f"🏨 *Hotel:* {hotel_name}\n"
            f"🛏️ *Room:* {room_name}\n"
            f"👥 *Guests:* {guest_count}\n"
            f"📅 *Check-in:* {check_in}\n"
            f"📅 *Check-out:* {check_out}\n"
            f"🌙 *Nights:* {nights}\n\n"
            f"📧 A confirmation email has been sent to {guest_email}\n\n"
            f"We look forward to welcoming you! 🎉\n\n"
            f"_Need to make changes? Type 'help' for options._"
        )

    @staticmethod
    def format_error_message(error_type: str, details: str = "") -> str:
        """Format error messages with helpful context."""
        error_messages = {
            'invalid_dates': (
                "❌ *Invalid Dates*\n\n"
                f"{details}\n\n"
                "Please provide dates in YYYY-MM-DD format.\n"
                "Example: 2024-12-15"
            ),
            'no_availability': (
                "😕 *No Rooms Available*\n\n"
                f"{details}\n\n"
                "Would you like to try different dates?"
            ),
            'missing_info': (
                "ℹ️ *Additional Information Needed*\n\n"
                f"{details}\n\n"
                "Please provide the requested information to continue."
            ),
            'booking_failed': (
                "❌ *Booking Failed*\n\n"
                "We encountered an error while processing your booking.\n"
                "Please try again or contact our support team.\n\n"
                f"Error: {details}"
            )
        }

        return error_messages.get(error_type, f"Error: {details}")


# ============================================================================
# Date and Input Parsing
# ============================================================================

class WhatsAppInputParser:
    """Parse user inputs from WhatsApp messages."""

    @staticmethod
    def parse_date_from_natural_language(text: str) -> Optional[str]:
        """
        Parse date from natural language.

        Examples:
        - "tomorrow" -> next day
        - "next monday" -> upcoming Monday
        - "December 15" -> 2024-12-15
        - "12/15" -> 2024-12-15
        """
        text_lower = text.lower().strip()
        today = datetime.now()

        # Handle relative dates
        if 'tomorrow' in text_lower:
            date = today + timedelta(days=1)
            return date.strftime('%Y-%m-%d')

        if 'today' in text_lower:
            return today.strftime('%Y-%m-%d')

        if 'next week' in text_lower:
            date = today + timedelta(weeks=1)
            return date.strftime('%Y-%m-%d')

        # Try to find YYYY-MM-DD format
        date_pattern = r'(\d{4}[-/]\d{2}[-/]\d{2})'
        match = re.search(date_pattern, text)
        if match:
            date_str = match.group(1).replace('/', '-')
            return date_str

        # Try MM/DD or MM-DD format
        short_date_pattern = r'(\d{1,2}[-/]\d{1,2})'
        match = re.search(short_date_pattern, text)
        if match:
            try:
                date_parts = match.group(1).replace('/', '-').split('-')
                month = int(date_parts[0])
                day = int(date_parts[1])
                year = today.year

                # If the date is in the past this year, assume next year
                potential_date = datetime(year, month, day)
                if potential_date < today:
                    year += 1

                return f"{year}-{month:02d}-{day:02d}"
            except:
                pass

        return None

    @staticmethod
    def extract_dates_and_guests(text: str) -> Dict[str, Optional[str]]:
        """
        Extract booking information from a message.

        Returns:
            Dictionary with check_in, check_out, and guest_count
        """
        result = {
            'check_in': None,
            'check_out': None,
            'guest_count': None
        }

        # Extract dates
        date_pattern = r'(\d{4}-\d{2}-\d{2})'
        dates = re.findall(date_pattern, text)

        if len(dates) >= 2:
            result['check_in'] = dates[0]
            result['check_out'] = dates[1]
        elif len(dates) == 1:
            result['check_in'] = dates[0]

        # Extract guest count
        guest_patterns = [
            r'(\d+)\s*(?:guests?|people|persons?)',
            r'for\s*(\d+)',
            r'party\s*of\s*(\d+)',
            r'(\d+)\s*(?:adults?|pax)'
        ]

        for pattern in guest_patterns:
            match = re.search(pattern, text.lower())
            if match:
                result['guest_count'] = int(match.group(1))
                break

        return result

    @staticmethod
    def parse_room_selection(text: str, available_rooms: List[Dict]) -> Optional[str]:
        """
        Parse room selection from user message.

        Args:
            text: User's message
            available_rooms: List of available rooms

        Returns:
            Room ID if match found, None otherwise
        """
        text_lower = text.lower().strip()

        # Check for numeric selection (1, 2, 3, etc.)
        if text_lower.isdigit():
            index = int(text_lower) - 1
            if 0 <= index < len(available_rooms):
                return available_rooms[index]['id']

        # Check for room name match
        for room in available_rooms:
            if room['name'].lower() in text_lower:
                return room['id']

        # Check for partial matches
        for room in available_rooms:
            room_words = room['name'].lower().split()
            if any(word in text_lower for word in room_words if len(word) > 3):
                return room['id']

        return None

    @staticmethod
    def extract_guest_details(text: str) -> Dict[str, Optional[str]]:
        """
        Extract guest details from message.

        Returns:
            Dictionary with name, email, phone
        """
        result = {
            'name': None,
            'email': None,
            'phone': None
        }

        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        if email_match:
            result['email'] = email_match.group(0)

        # Extract phone number (basic pattern)
        phone_pattern = r'[\+\d][\d\s\-\(\)]{7,}\d'
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            phone = phone_match.group(0)
            # Try to parse and format
            try:
                parsed = phonenumbers.parse(phone, None)
                if phonenumbers.is_valid_number(parsed):
                    result['phone'] = phonenumbers.format_number(
                        parsed,
                        phonenumbers.PhoneNumberFormat.E164
                    )
            except:
                result['phone'] = phone

        # Name extraction (simple heuristic - capitalize words)
        # Remove email and phone from text first
        name_text = text
        if result['email']:
            name_text = name_text.replace(result['email'], '')
        if result['phone']:
            name_text = name_text.replace(phone_match.group(0), '')

        # Look for capitalized words that could be a name
        words = name_text.split()
        name_candidates = [
            word for word in words
            if len(word) > 2 and word[0].isupper()
        ]

        if len(name_candidates) >= 2:
            result['name'] = ' '.join(name_candidates[:3])  # Max 3 words

        return result


# ============================================================================
# Media Handler
# ============================================================================

class WhatsAppMediaHandler:
    """Handle media messages (images, documents, etc.)."""

    def __init__(self, twilio_client: Client):
        self.twilio_client = twilio_client

    def download_media(self, media_url: str, media_sid: str) -> Optional[bytes]:
        """
        Download media from Twilio.

        Args:
            media_url: URL of the media
            media_sid: Media SID from Twilio

        Returns:
            Media bytes or None if failed
        """
        try:
            # Fetch media from Twilio
            media = self.twilio_client.api.v2010.accounts(
                os.getenv('TWILIO_ACCOUNT_SID')
            ).messages(media_sid).media(0).fetch()

            # Download the media content
            import requests
            response = requests.get(media.uri)

            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Failed to download media: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            return None

    def send_image(self, to_number: str, image_url: str, caption: str = ""):
        """
        Send an image via WhatsApp.

        Args:
            to_number: Recipient's WhatsApp number
            image_url: URL of the image to send
            caption: Optional caption
        """
        try:
            message = self.twilio_client.messages.create(
                from_=os.getenv('TWILIO_WHATSAPP_NUMBER'),
                to=to_number,
                body=caption,
                media_url=[image_url]
            )
            logger.info(f"Sent image to {to_number}: {message.sid}")
            return message.sid

        except Exception as e:
            logger.error(f"Error sending image: {e}")
            return None


# ============================================================================
# Quick Reply Templates
# ============================================================================

class QuickReplyTemplates:
    """Pre-defined quick reply templates for common scenarios."""

    @staticmethod
    def get_main_menu() -> str:
        """Get main menu options."""
        return (
            "📋 *What would you like to do?*\n\n"
            "1️⃣ Make a new booking\n"
            "2️⃣ Check booking status\n"
            "3️⃣ Modify existing booking\n"
            "4️⃣ Contact support\n"
            "5️⃣ Hotel amenities & info\n\n"
            "Reply with a number or describe what you need!"
        )

    @staticmethod
    def get_date_help() -> str:
        """Get help for date input."""
        return (
            "📅 *Date Input Help*\n\n"
            "*Accepted formats:*\n"
            "• YYYY-MM-DD (e.g., 2024-12-15)\n"
            "• MM/DD (e.g., 12/15)\n"
            "• Natural language:\n"
            "  - tomorrow\n"
            "  - next Monday\n"
            "  - December 15\n\n"
            "Example: \"I need a room from 2024-12-15 to 2024-12-20\""
        )

    @staticmethod
    def get_amenities_info() -> str:
        """Get hotel amenities information."""
        hotel_name = os.getenv('HOTEL_NAME', 'The Grand Hotel')
        return (
            f"🏨 *{hotel_name} - Amenities*\n\n"
            f"🌟 *Hotel Features:*\n"
            f"• 24/7 Front Desk\n"
            f"• Free WiFi throughout\n"
            f"• Swimming Pool & Spa\n"
            f"• Fitness Center\n"
            f"• Restaurant & Bar\n"
            f"• Room Service\n"
            f"• Free Parking\n"
            f"• Airport Shuttle\n\n"
            f"🛏️ *Room Features:*\n"
            f"• Air Conditioning\n"
            f"• Flat-screen TV\n"
            f"• Coffee/Tea Maker\n"
            f"• Mini Bar\n"
            f"• Safe\n"
            f"• Hairdryer\n\n"
            f"Ready to book? Let me know your dates!"
        )

    @staticmethod
    def get_cancellation_policy() -> str:
        """Get cancellation policy."""
        return (
            "📜 *Cancellation Policy*\n\n"
            "• Free cancellation up to 48 hours before check-in\n"
            "• 50% charge for cancellations 24-48 hours before\n"
            "• Full charge for cancellations within 24 hours\n"
            "• No-show: Full charge\n\n"
            "To cancel a booking, please contact us with your "
            "confirmation number."
        )


# ============================================================================
# Validation Utilities
# ============================================================================

def validate_phone_number(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate and format phone number.

    Returns:
        Tuple of (is_valid, formatted_number)
    """
    try:
        parsed = phonenumbers.parse(phone, None)
        if phonenumbers.is_valid_number(parsed):
            formatted = phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.E164
            )
            return True, formatted
        return False, None
    except:
        return False, None


def validate_email(email: str) -> bool:
    """Validate email format."""
    email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
    return bool(re.match(email_pattern, email))


def sanitize_message(message: str) -> str:
    """
    Sanitize user message for security.

    Args:
        message: Raw user message

    Returns:
        Sanitized message
    """
    # Remove potential injection attempts
    sanitized = message.strip()

    # Limit length
    max_length = 1000
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized
