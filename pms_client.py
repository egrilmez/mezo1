"""
QloApps Property Management System Client

This module provides integration with QloApps (Open Source Hotel PMS) via REST API.
Handles room availability checks and booking creation.
"""

import os
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import httpx
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class RoomType(BaseModel):
    """Represents a room type available in the hotel."""

    id: str
    name: str
    description: str
    price_per_night: float
    max_guests: int
    amenities: List[str] = Field(default_factory=list)
    available_count: int = 0


class BookingDetails(BaseModel):
    """Guest and booking information."""

    guest_name: str
    guest_email: str
    guest_phone: str
    check_in: str  # Format: YYYY-MM-DD
    check_out: str  # Format: YYYY-MM-DD
    guest_count: int
    special_requests: Optional[str] = None

    @validator('check_in', 'check_out')
    def validate_date_format(cls, v):
        """Ensure dates are in correct format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')


class QloAppsClient:
    """
    Client for interacting with QloApps Property Management System.

    QloApps API Documentation:
    - Base URL: https://your-instance.com/api/
    - Authentication: Webservice key via query parameter or header
    - Response Format: JSON or XML (configurable)

    Expected API Endpoints (QloApps PrestaShop-based structure):
    - GET /api/rooms?filter[date_from]=YYYY-MM-DD&filter[date_to]=YYYY-MM-DD
    - POST /api/bookings with booking details
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        mock_mode: bool = True
    ):
        """
        Initialize the QloApps client.

        Args:
            base_url: QloApps API base URL (e.g., https://hotel.com/api)
            api_key: Webservice authentication key
            timeout: Request timeout in seconds
            mock_mode: If True, return mock data instead of making real API calls
        """
        self.base_url = base_url or os.getenv('QLOAPPS_BASE_URL', 'http://localhost/api')
        self.api_key = api_key or os.getenv('QLOAPPS_API_KEY', 'mock_key')
        self.timeout = timeout
        self.mock_mode = mock_mode

        self.headers = {
            'Authorization': f'Basic {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        logger.info(
            f"QloApps client initialized - Base URL: {self.base_url}, "
            f"Mock Mode: {self.mock_mode}"
        )

    async def check_availability(
        self,
        check_in: str,
        check_out: str,
        guests: int
    ) -> List[Dict[str, Any]]:
        """
        Check room availability for given dates.

        Args:
            check_in: Check-in date in YYYY-MM-DD format
            check_out: Check-out date in YYYY-MM-DD format
            guests: Number of guests

        Returns:
            List of available rooms with details

        Expected QloApps API Response:
        {
            "rooms": [
                {
                    "id": "101",
                    "id_product": "1",
                    "name": "Deluxe Suite",
                    "description": "Luxurious suite with ocean view",
                    "price": 250.00,
                    "max_guests": 2,
                    "amenities": ["WiFi", "TV", "Mini Bar"],
                    "available": 3
                }
            ]
        }
        """
        if self.mock_mode:
            return self._mock_check_availability(check_in, check_out, guests)

        try:
            # Real API implementation
            params = {
                'date_from': check_in,
                'date_to': check_out,
                'occupancy': guests,
                'ws_key': self.api_key,
                'output_format': 'JSON'
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/rooms",
                    params=params,
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()

                # Transform QloApps response to standard format
                rooms = []
                for room in data.get('rooms', []):
                    rooms.append({
                        'id': str(room.get('id')),
                        'name': room.get('name', 'Unknown Room'),
                        'description': room.get('description', ''),
                        'price_per_night': float(room.get('price', 0)),
                        'max_guests': int(room.get('max_guests', 2)),
                        'amenities': room.get('amenities', []),
                        'available_count': int(room.get('available', 0))
                    })

                logger.info(f"Found {len(rooms)} available rooms for {check_in} to {check_out}")
                return rooms

        except httpx.HTTPError as e:
            logger.error(f"HTTP error checking availability: {e}")
            raise
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            raise

    def _mock_check_availability(
        self,
        check_in: str,
        check_out: str,
        guests: int
    ) -> List[Dict[str, Any]]:
        """Return mock room availability data."""

        # Calculate number of nights
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
        nights = (check_out_date - check_in_date).days

        mock_rooms = [
            {
                'id': 'room_101',
                'name': 'Standard Room',
                'description': 'Comfortable room with queen bed, city view',
                'price_per_night': 150.00,
                'total_price': 150.00 * nights,
                'max_guests': 2,
                'amenities': ['WiFi', 'TV', 'Air Conditioning', 'Coffee Maker'],
                'available_count': 5
            },
            {
                'id': 'room_201',
                'name': 'Deluxe Suite',
                'description': 'Spacious suite with king bed, ocean view, separate living area',
                'price_per_night': 250.00,
                'total_price': 250.00 * nights,
                'max_guests': 3,
                'amenities': ['WiFi', 'TV', 'Mini Bar', 'Balcony', 'Jacuzzi'],
                'available_count': 3
            },
            {
                'id': 'room_301',
                'name': 'Presidential Suite',
                'description': 'Luxurious suite with panoramic views, private terrace',
                'price_per_night': 500.00,
                'total_price': 500.00 * nights,
                'max_guests': 4,
                'amenities': ['WiFi', 'TV', 'Mini Bar', 'Private Terrace', 'Butler Service'],
                'available_count': 1
            }
        ]

        # Filter rooms based on guest count
        available_rooms = [
            room for room in mock_rooms
            if room['max_guests'] >= guests and room['available_count'] > 0
        ]

        logger.info(
            f"Mock: Found {len(available_rooms)} rooms for {guests} guests "
            f"from {check_in} to {check_out}"
        )

        return available_rooms

    async def create_booking(
        self,
        guest_details: Dict[str, Any],
        room_id: str
    ) -> str:
        """
        Create a new booking in the PMS.

        Args:
            guest_details: Dictionary containing guest information
                Required keys: guest_name, guest_email, guest_phone,
                              check_in, check_out, guest_count
                Optional: special_requests
            room_id: ID of the room to book

        Returns:
            Booking confirmation number/ID

        Expected QloApps API Request Body:
        {
            "booking": {
                "id_room": "101",
                "date_from": "2024-12-01",
                "date_to": "2024-12-05",
                "id_customer": "new",
                "customer": {
                    "firstname": "John",
                    "lastname": "Doe",
                    "email": "john@example.com",
                    "phone": "+1234567890"
                },
                "total_rooms": 1,
                "occupancy": 2,
                "comment": "Special requests here"
            }
        }

        Expected Response:
        {
            "booking": {
                "id": "BK123456",
                "status": "confirmed",
                "confirmation_number": "CONF-2024-001"
            }
        }
        """
        # Validate guest details
        try:
            booking = BookingDetails(**guest_details)
        except Exception as e:
            logger.error(f"Invalid booking details: {e}")
            raise ValueError(f"Invalid booking details: {e}")

        if self.mock_mode:
            return self._mock_create_booking(guest_details, room_id)

        try:
            # Parse guest name
            name_parts = booking.guest_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            # Prepare booking payload for QloApps
            payload = {
                'booking': {
                    'id_room': room_id,
                    'date_from': booking.check_in,
                    'date_to': booking.check_out,
                    'id_customer': 'new',
                    'customer': {
                        'firstname': first_name,
                        'lastname': last_name,
                        'email': booking.guest_email,
                        'phone': booking.guest_phone
                    },
                    'total_rooms': 1,
                    'occupancy': booking.guest_count,
                    'comment': booking.special_requests or ''
                }
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/bookings",
                    json=payload,
                    headers=self.headers,
                    params={'ws_key': self.api_key}
                )
                response.raise_for_status()
                data = response.json()

                # Extract confirmation number from response
                booking_data = data.get('booking', {})
                confirmation_number = booking_data.get('confirmation_number') or booking_data.get('id')

                logger.info(f"Booking created successfully: {confirmation_number}")
                return confirmation_number

        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating booking: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            raise

    def _mock_create_booking(
        self,
        guest_details: Dict[str, Any],
        room_id: str
    ) -> str:
        """Return mock booking confirmation."""

        import random

        # Generate mock confirmation number
        confirmation_number = f"CONF-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

        logger.info(
            f"Mock booking created: {confirmation_number} for "
            f"{guest_details.get('guest_name')} in room {room_id}"
        )

        return confirmation_number

    async def get_booking_details(self, confirmation_number: str) -> Dict[str, Any]:
        """
        Retrieve booking details by confirmation number.

        Args:
            confirmation_number: Booking confirmation number

        Returns:
            Dictionary with booking details
        """
        if self.mock_mode:
            return {
                'confirmation_number': confirmation_number,
                'status': 'confirmed',
                'check_in': '2024-12-01',
                'check_out': '2024-12-05',
                'room': 'Deluxe Suite',
                'guest_name': 'John Doe'
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/bookings/{confirmation_number}",
                    headers=self.headers,
                    params={'ws_key': self.api_key}
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error retrieving booking: {e}")
            raise

    async def cancel_booking(self, confirmation_number: str) -> bool:
        """
        Cancel an existing booking.

        Args:
            confirmation_number: Booking confirmation number

        Returns:
            True if cancellation successful
        """
        if self.mock_mode:
            logger.info(f"Mock: Booking {confirmation_number} cancelled")
            return True

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/bookings/{confirmation_number}",
                    headers=self.headers,
                    params={'ws_key': self.api_key}
                )
                response.raise_for_status()
                return True

        except Exception as e:
            logger.error(f"Error cancelling booking: {e}")
            raise
