# 🚀 Quick Start with Docker

Get the Hotel Reservation Agent running in 3 minutes!

## Prerequisites

- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed (included with Docker Desktop)

## Step 1: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
```

**Minimum required for WhatsApp:**
```env
GROQ_API_KEY=your_groq_key_here
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_token_here
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

Get API keys:
- **Groq**: https://groq.com (free tier available)
- **Twilio**: https://twilio.com/try-twilio (free trial)

## Step 2: Start Services

### Option A: Interactive Script (Recommended)

```bash
./start.sh
```

Follow the prompts to select which services to start.

### Option B: Using Make Commands

```bash
# Start WhatsApp bot
make up-whatsapp

# Or start voice agent
make up-voice

# Or start both
make up-all
```

### Option C: Direct Docker Compose

```bash
# Build images
docker-compose build

# Start WhatsApp bot
docker-compose up -d hotel-redis hotel-whatsapp-bot

# Check status
docker-compose ps
```

## Step 3: Verify It's Running

```bash
# Check health
curl http://localhost:5000/health

# Expected output:
# {
#   "status": "healthy",
#   "service": "whatsapp-hotel-bot",
#   "redis": "connected"
# }
```

## Step 4: Configure WhatsApp Webhook

### For Development (using ngrok):

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Expose your local server
ngrok http 5000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

### Configure in Twilio:

1. Go to [Twilio Console](https://console.twilio.com)
2. Navigate to: Messaging → Settings → WhatsApp Sandbox Settings
3. Set "When a message comes in" to: `https://your-ngrok-url.ngrok.io/webhook/whatsapp`
4. Save

## Step 5: Test It!

Send a WhatsApp message to your Twilio sandbox number:

```
You: Hi

Bot: 🏨 Welcome to The Grand Hotel!
     I'm your AI assistant...
```

## 🎯 Common Commands

```bash
# View logs
make logs-whatsapp

# Check service health
make health

# Restart services
make restart

# Stop services
make down

# Clean everything
make clean
```

## 📊 View Logs

```bash
# All services
docker-compose logs -f

# WhatsApp bot only
docker-compose logs -f hotel-whatsapp-bot

# Last 100 lines
docker-compose logs --tail=100 hotel-whatsapp-bot
```

## 🔧 Troubleshooting

### Services won't start?

```bash
# Check Docker is running
docker ps

# Check logs
make logs-whatsapp

# Rebuild images
docker-compose build --no-cache
make up-whatsapp
```

### Port 5000 already in use?

```bash
# Find what's using it
sudo lsof -i :5000

# Or change port in docker-compose.yml:
ports:
  - "5001:5000"
```

### Redis connection failed?

```bash
# Check Redis is running
docker-compose ps hotel-redis

# Test Redis
docker-compose exec hotel-redis redis-cli ping
# Should return: PONG
```

## 🛑 Stopping Services

```bash
# Stop all services
./stop.sh

# Or with make
make down

# Stop and remove volumes (clears all data)
docker-compose down -v
```

## 📁 Project Structure

```
.
├── agent.py                 # Voice agent (LiveKit)
├── whatsapp_bot.py         # WhatsApp bot (Flask)
├── state_graph.py          # LangGraph state machine
├── pms_client.py           # Hotel PMS integration
├── Dockerfile              # Container image definition
├── docker-compose.yml      # Service orchestration
├── start.sh                # Easy start script
└── .env                    # Your configuration
```

## 🌐 Access Points

Once running:

- **WhatsApp Bot Health**: http://localhost:5000/health
- **WhatsApp Webhook**: http://localhost:5000/webhook/whatsapp
- **Redis**: localhost:6379

## 📖 Additional Resources

- **Full Docker Guide**: See `DOCKER_SETUP.md`
- **WhatsApp Integration**: See `WHATSAPP_INTEGRATION.md`
- **Voice Agent Setup**: See `HOTEL_VOICE_AGENT_README.md`

## 🆘 Need Help?

1. Check logs: `make logs-whatsapp`
2. Verify config: `cat .env`
3. Test health: `make health`
4. Review documentation: `DOCKER_SETUP.md`

## ✨ What's Next?

- Customize hotel name and settings in `.env`
- Connect to real PMS (set `PMS_MOCK_MODE=false`)
- Deploy to production (see `DOCKER_SETUP.md`)
- Add SSL/HTTPS with nginx
- Scale with Docker Swarm or Kubernetes

---

**Happy hosting! 🎉**

For production deployment, scaling, monitoring, and advanced features, see `DOCKER_SETUP.md`.
