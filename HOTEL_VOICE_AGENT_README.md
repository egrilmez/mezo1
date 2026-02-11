# Voice-Governed Hotel Reservation Agent

A production-ready, real-time voice agent for hotel reservations using LiveKit, LangGraph, and Groq.

## Overview

This project implements an AI-powered voice agent that handles hotel reservations through natural conversation. The agent uses state-of-the-art AI technologies for ultra-low latency voice interactions while maintaining strict conversation flow control through a finite state machine.

### Key Features

- **Real-Time Voice Communication**: WebRTC-based voice interaction via LiveKit
- **Low Latency**: Optimized pipeline with Deepgram (STT), Cartesia (TTS), and Groq (LLM)
- **Conversation Governance**: LangGraph state machine ensures proper booking flow
- **PMS Integration**: Direct integration with QloApps Property Management System
- **Interruption Handling**: Supports natural conversation with barge-in capabilities
- **Phone Call Support**: Automatic detection and greeting for SIP/phone calls

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     LiveKit Voice Agent                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐│
│  │  Silero  │───▶│ Deepgram │───▶│  Groq    │───▶│Cartesia││
│  │   VAD    │    │   STT    │    │  LLM     │    │  TTS   ││
│  └──────────┘    └──────────┘    └──────────┘    └────────┘│
│                                    │                         │
│                                    ▼                         │
│                          ┌──────────────────┐               │
│                          │   LangGraph      │               │
│                          │  State Machine   │               │
│                          └──────────────────┘               │
│                                    │                         │
│                                    ▼                         │
│                          ┌──────────────────┐               │
│                          │   QloApps PMS    │               │
│                          │     Client       │               │
│                          └──────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Orchestration | LiveKit Agents | WebRTC/Voice pipeline management |
| Speech-to-Text | Deepgram Nova-2 | Real-time transcription |
| Text-to-Speech | Cartesia Sonic | Ultra-low latency synthesis |
| LLM | Llama 3.1 70B (Groq) | Natural language understanding |
| State Management | LangGraph | Conversation flow control |
| PMS Backend | QloApps | Hotel booking system |
| VAD | Silero | Voice activity detection |

## Conversation Flow

The agent follows a strict state machine to ensure all necessary information is collected:

```
1. Greeting
   ↓
2. Collect Dates (Check-in, Check-out, Guest Count)
   ↓
3. Validate Dates (Not in past, check-out > check-in)
   ↓
4. Check Availability (Query PMS)
   ↓
5. Present Options (Available rooms)
   ↓
6. Collect Room Selection
   ↓
7. Collect Guest Details (Name, Email, Phone)
   ↓
8. Create Booking (Via PMS)
   ↓
9. Confirmation
```

## Installation

### Prerequisites

- Python 3.10+
- LiveKit Cloud account or self-hosted instance
- API keys for:
  - Deepgram
  - Cartesia
  - Groq
  - QloApps (optional for mock mode)

### Setup

1. **Clone the repository**

```bash
git clone <repository-url>
cd hotel-voice-agent
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-instance.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

# API Keys
DEEPGRAM_API_KEY=your_deepgram_api_key
CARTESIA_API_KEY=your_cartesia_api_key
GROQ_API_KEY=your_groq_api_key

# QloApps (optional for production)
QLOAPPS_BASE_URL=https://your-qloapps-instance.com/api
QLOAPPS_API_KEY=your_qloapps_webservice_key

# Hotel Configuration
HOTEL_NAME=The Grand Hotel
```

## Usage

### Running the Agent

Start the LiveKit worker:

```bash
python agent.py
```

The agent will connect to your LiveKit instance and wait for incoming calls.

### Testing with LiveKit Playground

1. Go to your LiveKit Cloud dashboard
2. Navigate to the Playground
3. Connect to a room
4. The agent will automatically join and greet you

### Testing Phone Calls

For SIP/Phone integration:

1. Configure SIP trunk in LiveKit
2. Rooms starting with `call-` trigger automatic greeting
3. The agent will immediately greet callers

### Example Conversation

```
Agent: Hello! Thank you for calling The Grand Hotel. I'm here to help you
       make a reservation. When would you like to check in?

User: I'd like to book a room from December 1st to December 5th for 2 people.

Agent: Great! I found 3 available rooms for 2 guests from 2024-12-01 to
       2024-12-05:

       1. Standard Room - $150/night
          Comfortable room with queen bed, city view
          Amenities: WiFi, TV, Air Conditioning, Coffee Maker

       2. Deluxe Suite - $250/night
          Spacious suite with king bed, ocean view
          Amenities: WiFi, TV, Mini Bar, Balcony, Jacuzzi

       3. Presidential Suite - $500/night
          Luxurious suite with panoramic views
          Amenities: WiFi, TV, Mini Bar, Private Terrace, Butler Service

       Which room would you like to book?

User: I'll take the Deluxe Suite.

Agent: Excellent choice! To complete your booking, I'll need a few details.
       What's your full name?

User: John Smith

Agent: Thank you, John. What's your email address?

User: john.smith@email.com

Agent: And your phone number?

User: 555-123-4567

Agent: Excellent! Your booking is confirmed.

       Confirmation Number: CONF-20241201-1234
       Room: Deluxe Suite
       Check-in: 2024-12-01
       Check-out: 2024-12-05
       Guests: 2

       A confirmation email has been sent to john.smith@email.com.
       We look forward to welcoming you to The Grand Hotel!
```

## Project Structure

```
hotel-voice-agent/
├── agent.py              # Main LiveKit agent entry point
├── state_graph.py        # LangGraph state machine definition
├── pms_client.py         # QloApps PMS integration
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
├── .env                  # Your configuration (not in git)
└── HOTEL_VOICE_AGENT_README.md  # This file
```

## Configuration

### Agent Behavior

Modify these environment variables to customize behavior:

```env
# Enable/disable interruptions
ENABLE_INTERRUPTIONS=true

# VAD sensitivity (0.0 - 1.0)
VAD_THRESHOLD=0.5

# Logging level
LOG_LEVEL=INFO

# Hotel information
HOTEL_NAME=The Grand Hotel
HOTEL_TIMEZONE=America/New_York
```

### Voice Customization

Edit `agent.py` to change TTS voice:

```python
tts=cartesia.TTS(
    api_key=os.getenv('CARTESIA_API_KEY'),
    voice="79a125e8-cd45-4c13-8a67-188112f4dd22",  # Change voice ID
    model="sonic-english",
    encoding="pcm_s16le",
    sample_rate=24000,
)
```

Available Cartesia voices:
- `79a125e8-cd45-4c13-8a67-188112f4dd22`: Professional female
- `a0e99841-438c-4a64-b679-ae501e7d6091`: Professional male
- See Cartesia docs for more options

## QloApps Integration

### Mock Mode (Default)

The agent runs in mock mode by default, returning simulated room availability and bookings.

### Production Mode

To connect to a real QloApps instance:

1. Set up QloApps webservice:
   - Enable webservice in QloApps admin
   - Generate API key
   - Configure permissions

2. Update `.env`:
   ```env
   QLOAPPS_BASE_URL=https://your-hotel.com/api
   QLOAPPS_API_KEY=YOUR_WEBSERVICE_KEY
   ```

3. Disable mock mode in `agent.py`:
   ```python
   self.pms_client = QloAppsClient(
       base_url=os.getenv('QLOAPPS_BASE_URL'),
       api_key=os.getenv('QLOAPPS_API_KEY'),
       mock_mode=False  # Set to False
   )
   ```

### QloApps API Endpoints Used

- `GET /api/rooms?date_from=...&date_to=...&occupancy=...`
- `POST /api/bookings`
- `GET /api/bookings/{id}`
- `DELETE /api/bookings/{id}`

## Development

### Running in Development

```bash
# With debug logging
LOG_LEVEL=DEBUG python agent.py

# Test specific components
python -c "from pms_client import QloAppsClient; import asyncio; asyncio.run(QloAppsClient(mock_mode=True).check_availability('2024-12-01', '2024-12-05', 2))"
```

### Code Style

The project follows PEP 8 standards. Format code with:

```bash
black agent.py state_graph.py pms_client.py
```

### Testing

Create test scripts for components:

```python
# test_pms.py
import asyncio
from pms_client import QloAppsClient

async def test_availability():
    client = QloAppsClient(mock_mode=True)
    rooms = await client.check_availability('2024-12-01', '2024-12-05', 2)
    print(f"Found {len(rooms)} rooms")
    for room in rooms:
        print(f"  - {room['name']}: ${room['price_per_night']}/night")

asyncio.run(test_availability())
```

## Performance Optimization

### Latency Reduction

The agent is optimized for minimal latency:

1. **Groq**: Uses Llama 3.1 70B with fast inference
2. **Cartesia**: Ultra-low latency TTS (~100ms)
3. **Deepgram**: Real-time STT with interim results disabled for accuracy
4. **Streaming**: TTS receives LLM output as stream for immediate playback

### Scalability

- Each LiveKit worker can handle multiple concurrent sessions
- Stateless design allows horizontal scaling
- LangGraph state is session-scoped

## Troubleshooting

### Common Issues

**Issue**: Agent doesn't respond

```bash
# Check LiveKit connection
Check LIVEKIT_URL, API_KEY, and API_SECRET in .env

# Check logs
LOG_LEVEL=DEBUG python agent.py
```

**Issue**: Poor transcription quality

```bash
# Adjust VAD threshold
VAD_THRESHOLD=0.3  # Lower = more sensitive
```

**Issue**: Slow response times

```bash
# Verify Groq API key
# Check network latency to services
# Consider using dedicated LiveKit instance
```

## Security Considerations

1. **API Keys**: Never commit `.env` file
2. **PMS Access**: Use read-only keys when possible
3. **Data Privacy**: Implement proper logging controls for PII
4. **Rate Limiting**: Configure appropriate limits for production

## Production Deployment

### Recommended Setup

1. **LiveKit**: Use LiveKit Cloud or dedicated instance
2. **Monitoring**: Implement logging and metrics
3. **Error Handling**: Set up alerts for failures
4. **Backup**: Ensure PMS has redundancy
5. **Testing**: Test with real phone calls before launch

### Deployment Checklist

- [ ] All API keys configured
- [ ] QloApps integration tested
- [ ] Voice quality verified
- [ ] Conversation flows tested
- [ ] Error handling validated
- [ ] Monitoring configured
- [ ] Backup procedures in place
- [ ] Load testing completed

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review LiveKit documentation: https://docs.livekit.io
3. Check LangGraph docs: https://langchain-ai.github.io/langgraph/
4. Review QloApps API docs: https://qloapps.com/qlo-reservation-system/

## License

[Your License Here]

## Acknowledgments

- LiveKit for real-time infrastructure
- Deepgram for speech recognition
- Cartesia for text-to-speech
- Groq for LLM inference
- LangChain/LangGraph for orchestration
- QloApps for PMS functionality
