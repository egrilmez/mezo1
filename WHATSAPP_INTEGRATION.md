# WhatsApp Integration for Hotel Reservation Agent

Complete guide for integrating the hotel reservation agent with WhatsApp using Twilio.

## Overview

The WhatsApp integration allows guests to make hotel reservations through natural text conversations on WhatsApp. It uses the same LangGraph state machine as the voice agent, ensuring consistent booking flows across channels.

### Features

- **Natural Conversation**: Text-based booking through WhatsApp
- **Session Management**: Redis-based session persistence
- **Rich Formatting**: WhatsApp markdown for better readability
- **Quick Commands**: Help, status, reset functionality
- **Media Support**: Ability to send/receive images and documents
- **Multi-language Ready**: Extensible for multiple languages
- **Persistent State**: Conversations persist across sessions

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    WhatsApp User                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Twilio WhatsApp API                     │
└────────────────────┬────────────────────────────────────┘
                     │ (Webhook)
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Flask Webhook Handler                       │
│                (whatsapp_bot.py)                         │
├─────────────────────────────────────────────────────────┤
│  • Message routing                                       │
│  • Session management (Redis)                            │
│  • Command handling                                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              LangGraph State Machine                     │
│                (state_graph.py)                          │
├─────────────────────────────────────────────────────────┤
│  Greeting → Dates → Validation → Availability →         │
│  Room Selection → Guest Info → Booking → Confirmation   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              QloApps PMS Client                          │
│                (pms_client.py)                           │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Twilio Account** with WhatsApp enabled
   - Sign up at https://www.twilio.com
   - Set up WhatsApp sandbox or production number

2. **Redis Server** for session management
   - Local: `sudo apt install redis-server`
   - Cloud: Redis Cloud, AWS ElastiCache, etc.

3. **Public Webhook URL**
   - Use ngrok for development
   - Production: Deploy to cloud with HTTPS

4. **Environment Variables**
   - All from voice agent setup
   - Additional WhatsApp/Twilio credentials

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies for WhatsApp:
- `twilio` - WhatsApp API client
- `flask` - Webhook server
- `redis` - Session storage
- `phonenumbers` - Phone validation

### 2. Configure Environment

Update your `.env` file:

```env
# Twilio WhatsApp Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Webhook Server
WHATSAPP_BOT_PORT=5000
FLASK_DEBUG=false

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
SESSION_TTL_SECONDS=3600  # 1 hour

# PMS
PMS_MOCK_MODE=true  # Set to false for production
```

### 3. Set Up Twilio

#### Option A: WhatsApp Sandbox (Development)

1. Go to Twilio Console → Messaging → Try it out → Send a WhatsApp message
2. Follow instructions to join sandbox (send code to sandbox number)
3. Use sandbox number as `TWILIO_WHATSAPP_NUMBER`

#### Option B: Production WhatsApp Number

1. Request WhatsApp Business Account approval from Twilio
2. Complete Facebook Business verification
3. Submit message templates for approval
4. Configure production number

### 4. Start Redis

```bash
# Start Redis server
redis-server

# Verify it's running
redis-cli ping
# Should return: PONG
```

### 5. Set Up Webhook

#### Development (ngrok)

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Start ngrok tunnel
ngrok http 5000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

#### Production

Deploy to cloud platform with HTTPS:
- Heroku
- AWS Lambda + API Gateway
- Google Cloud Run
- DigitalOcean App Platform

### 6. Configure Twilio Webhook

1. Go to Twilio Console → Messaging → Settings → WhatsApp Sandbox Settings
2. Set "When a message comes in" to: `https://your-domain.com/webhook/whatsapp`
3. Set HTTP method to: `POST`
4. Save configuration

## Running the Bot

### Start the WhatsApp Bot

```bash
python whatsapp_bot.py
```

Expected output:
```
INFO - Starting WhatsApp Hotel Bot
INFO - Hotel: The Grand Hotel
INFO - WhatsApp Number: whatsapp:+14155238886
INFO - Running on http://0.0.0.0:5000
```

### Test the Integration

1. Send a message to your WhatsApp number
2. You should receive a greeting
3. Start a booking conversation

Example conversation:
```
You: Hi
Bot: 🏨 Welcome to The Grand Hotel!
     I'm your AI assistant...

You: I need a room from 2024-12-15 to 2024-12-20 for 2 guests
Bot: Great! I found 3 available rooms...

You: I'll take the deluxe suite
Bot: Excellent choice! To complete your booking...
```

## Usage

### User Commands

Users can send these special commands:

| Command | Description |
|---------|-------------|
| `help` | Show help menu |
| `reset` | Start new booking |
| `status` | Check current booking status |
| `menu` | Show main menu |

### Conversation Flow

1. **Greeting**: Bot welcomes user
2. **Date Collection**: User provides check-in, check-out, guests
3. **Validation**: Dates validated
4. **Availability**: Bot shows available rooms
5. **Room Selection**: User picks a room
6. **Guest Info**: Bot collects name, email, phone
7. **Booking**: Reservation created
8. **Confirmation**: Confirmation number sent

### Message Formatting

The bot uses WhatsApp formatting:

- `*Bold text*` for emphasis
- `_Italic text_` for notes
- Emojis for visual clarity
- Structured lists for room options

## API Endpoints

### Webhook Endpoints

**POST /webhook/whatsapp**
- Receives incoming WhatsApp messages
- Processes through state machine
- Sends response back to user

**POST /webhook/status**
- Receives message delivery status updates
- Logs message status

**GET /health**
- Health check endpoint
- Returns service status

### Management Endpoints

**POST /api/send-message**
```json
{
  "to": "+1234567890",
  "message": "Your booking is confirmed!"
}
```

**DELETE /api/clear-session/{user_id}**
- Clear a user's session (admin)

## Session Management

### How Sessions Work

1. Each user identified by phone number
2. State stored in Redis with 1-hour TTL
3. Sessions automatically expire after inactivity
4. Users can manually reset with `reset` command

### Redis Keys

- Format: `whatsapp_session:{phone_number}`
- Contains: Complete AgentState
- TTL: Configurable via `SESSION_TTL_SECONDS`

### Session Data

```json
{
  "messages": [...],
  "check_in_date": "2024-12-15",
  "check_out_date": "2024-12-20",
  "guest_count": 2,
  "selected_room_id": "room_201",
  "guest_name": "John Smith",
  "guest_email": "john@example.com",
  "guest_phone": "+1234567890",
  "booking_status": "confirmed",
  "confirmation_number": "CONF-20241215-1234"
}
```

## Production Deployment

### Recommended Architecture

```
Internet
   │
   ├─→ Load Balancer (HTTPS)
   │      │
   │      ├─→ Flask App (Instance 1)
   │      ├─→ Flask App (Instance 2)
   │      └─→ Flask App (Instance 3)
   │
   └─→ Redis Cluster (Session Store)
```

### Deployment Checklist

- [ ] Set up production Redis (Redis Cloud, ElastiCache)
- [ ] Deploy Flask app with gunicorn
- [ ] Configure HTTPS/SSL certificates
- [ ] Set up load balancer
- [ ] Configure auto-scaling
- [ ] Set up monitoring and alerts
- [ ] Enable logging (Sentry, CloudWatch)
- [ ] Configure rate limiting
- [ ] Set up backup strategy
- [ ] Test failover scenarios

### Gunicorn Configuration

Create `gunicorn.conf.py`:

```python
bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync"
timeout = 120
keepalive = 5
errorlog = "-"
accesslog = "-"
loglevel = "info"
```

Run with:
```bash
gunicorn -c gunicorn.conf.py whatsapp_bot:app
```

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "whatsapp_bot:app"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  whatsapp-bot:
    build: .
    ports:
      - "5000:5000"
    environment:
      - REDIS_HOST=redis
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  redis-data:
```

Run with:
```bash
docker-compose up -d
```

## Advanced Features

### Message Templates

For production WhatsApp, use approved templates:

```python
from twilio.rest import Client

client = Client(account_sid, auth_token)

message = client.messages.create(
    from_='whatsapp:+14155238886',
    content_sid='HXb5b62575e6e4ff6129ad7c8efe1f983e',
    content_variables='{"1":"John","2":"CONF-123"}',
    to='whatsapp:+1234567890'
)
```

### Media Messages

Send room images:

```python
from whatsapp_handler import WhatsAppMediaHandler

media_handler = WhatsAppMediaHandler(twilio_client)
media_handler.send_image(
    to_number='whatsapp:+1234567890',
    image_url='https://hotel.com/images/deluxe-suite.jpg',
    caption='Your selected room: Deluxe Suite'
)
```

### Proactive Messages

Send booking reminders:

```python
import requests

requests.post('http://localhost:5000/api/send-message', json={
    'to': '+1234567890',
    'message': '🔔 Reminder: Your check-in is tomorrow at The Grand Hotel!'
})
```

## Monitoring and Logging

### Health Checks

```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "service": "whatsapp-hotel-bot",
  "timestamp": "2024-12-01T12:00:00",
  "redis": "connected",
  "hotel": "The Grand Hotel"
}
```

### Metrics to Monitor

- Message volume (messages/minute)
- Response latency
- Booking conversion rate
- Session duration
- Error rate
- Redis connection status
- API response times

### Recommended Tools

- **Logging**: Sentry, Loggly
- **Metrics**: Prometheus + Grafana
- **Uptime**: Pingdom, UptimeRobot
- **APM**: New Relic, DataDog

## Troubleshooting

### Common Issues

**Issue**: Webhook not receiving messages

```bash
# Check ngrok is running
curl http://localhost:4040/api/tunnels

# Verify webhook URL in Twilio console
# Check Flask logs for incoming requests
```

**Issue**: Redis connection failed

```bash
# Check Redis is running
redis-cli ping

# Check connection settings
echo $REDIS_HOST
echo $REDIS_PORT
```

**Issue**: Bot not responding

```bash
# Check logs
tail -f whatsapp_bot.log

# Verify environment variables
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('TWILIO_ACCOUNT_SID'))"

# Test Twilio credentials
python -c "from twilio.rest import Client; Client('ACxxx', 'token').api.accounts.list()"
```

**Issue**: State not persisting

```bash
# Check Redis
redis-cli
> KEYS whatsapp_session:*
> GET whatsapp_session:+1234567890

# Check TTL
> TTL whatsapp_session:+1234567890
```

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG python whatsapp_bot.py
```

### Testing Locally

Use ngrok for local testing:

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start bot
python whatsapp_bot.py

# Terminal 3: Start ngrok
ngrok http 5000
```

## Security Best Practices

1. **Validate Webhook Requests**
   - Verify Twilio signatures
   - Implement request validation

2. **Rate Limiting**
   - Limit messages per user
   - Prevent spam/abuse

3. **Data Privacy**
   - Encrypt sensitive data in Redis
   - Don't log PII
   - Implement data retention policy

4. **Access Control**
   - Secure admin endpoints
   - Use API keys for management APIs

5. **Input Validation**
   - Sanitize all user inputs
   - Prevent injection attacks

## Cost Optimization

### Twilio Costs

- WhatsApp conversations: $0.005 per user-initiated conversation
- Templates: $0.0042 per business-initiated message
- Free tier: Test with sandbox

### Redis Costs

- Self-hosted: Free (server costs only)
- Redis Cloud: Free tier available
- AWS ElastiCache: ~$15/month (t3.micro)

### Tips

- Set appropriate session TTLs
- Clean up old sessions regularly
- Use Redis persistence for important data
- Monitor usage to avoid surprises

## FAQ

**Q: Can I use this without Twilio?**
A: Yes, adapt to other providers (MessageBird, 360Dialog, etc.)

**Q: How many concurrent users can it handle?**
A: Depends on infrastructure. Single instance: ~100 concurrent users

**Q: Can I use multiple languages?**
A: Yes, extend the LangGraph prompts for multilingual support

**Q: Is it GDPR compliant?**
A: You must implement proper data handling, retention, and deletion

**Q: Can I integrate with my existing PMS?**
A: Yes, modify `pms_client.py` for your PMS API

## Support

For issues:
1. Check troubleshooting section
2. Review logs
3. Test with Twilio console
4. Check Redis connection
5. Verify webhook configuration

## Resources

- Twilio WhatsApp API: https://www.twilio.com/docs/whatsapp
- Flask Documentation: https://flask.palletsprojects.com/
- Redis Documentation: https://redis.io/documentation
- LangGraph Documentation: https://langchain-ai.github.io/langgraph/

## License

[Your License Here]
