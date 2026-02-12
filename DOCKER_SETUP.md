# Docker Setup Guide - Hotel Reservation Agent

Complete guide for running the hotel reservation agent using Docker.

## Overview

The dockerized setup includes:
- **WhatsApp Bot**: Flask app with Gunicorn (Port 5000)
- **Voice Agent**: LiveKit voice pipeline
- **Redis**: Session storage for WhatsApp
- **All dependencies**: Pre-installed in containers

## Quick Start

### 1. Prerequisites

- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- `.env` file configured with API keys

```bash
# Check Docker installation
docker --version
docker-compose --version
```

### 2. Configure Environment

```bash
# Create .env from example
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Minimum required for WhatsApp:
```env
GROQ_API_KEY=your_groq_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

### 3. Build and Run

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d hotel-redis hotel-whatsapp-bot

# Check status
docker-compose ps

# View logs
docker-compose logs -f hotel-whatsapp-bot
```

### 4. Verify It's Working

```bash
# Health check
curl http://localhost:5000/health

# Expected output:
# {
#   "status": "healthy",
#   "service": "whatsapp-hotel-bot",
#   "redis": "connected"
# }
```

## Using Makefile (Recommended)

We provide a Makefile for easier management:

```bash
# Show all commands
make help

# Build images
make build

# Start WhatsApp bot
make up-whatsapp

# Start voice agent (requires LiveKit keys)
make up-voice

# View logs
make logs-whatsapp

# Check health
make health

# Stop all services
make down

# Clean everything
make clean
```

## Service Details

### WhatsApp Bot Container

**Image**: Custom Python 3.11
**Port**: 5000
**Dependencies**: Redis
**Command**: `gunicorn -c gunicorn.conf.py whatsapp_bot:app`

Configuration:
- 4 Gunicorn workers (CPU * 2 + 1)
- 120s timeout
- Auto-restart on failure
- Health checks every 30s

### Voice Agent Container

**Image**: Custom Python 3.11
**Dependencies**: None (connects to external LiveKit)
**Command**: `python agent.py`

**Note**: Voice agent runs with `--profile voice` flag

### Redis Container

**Image**: redis:7-alpine
**Port**: 6379
**Persistence**: Volume-backed with AOF
**Health checks**: Every 10s

## Docker Commands

### Starting Services

```bash
# Start WhatsApp bot only
docker-compose up -d hotel-redis hotel-whatsapp-bot

# Start voice agent only
docker-compose up -d hotel-voice-agent

# Start both
docker-compose --profile voice up -d

# Start in foreground (see logs)
docker-compose up hotel-redis hotel-whatsapp-bot
```

### Stopping Services

```bash
# Stop all
docker-compose down

# Stop specific service
docker-compose stop hotel-whatsapp-bot

# Stop and remove volumes
docker-compose down -v
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f hotel-whatsapp-bot

# Last 100 lines
docker-compose logs --tail=100 hotel-whatsapp-bot

# Since timestamp
docker-compose logs --since 2024-12-01T10:00:00 hotel-whatsapp-bot
```

### Managing Containers

```bash
# List running containers
docker-compose ps

# Restart service
docker-compose restart hotel-whatsapp-bot

# Rebuild and restart
docker-compose up -d --build hotel-whatsapp-bot

# View resource usage
docker stats hotel-whatsapp-bot hotel-redis
```

### Accessing Containers

```bash
# Open shell in WhatsApp bot
docker-compose exec hotel-whatsapp-bot /bin/bash

# Run Python command
docker-compose exec hotel-whatsapp-bot python -c "print('Hello')"

# Access Redis CLI
docker-compose exec hotel-redis redis-cli

# Check Redis keys
docker-compose exec hotel-redis redis-cli KEYS "whatsapp_session:*"
```

## Development Workflow

### Local Development with Hot Reload

```bash
# Mount local code as volume
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Or edit docker-compose.yml to add:
volumes:
  - .:/app
environment:
  - GUNICORN_RELOAD=true
```

### Testing

```bash
# Run tests in container
docker-compose exec hotel-whatsapp-bot python -m pytest

# Run specific test
docker-compose exec hotel-whatsapp-bot python -m pytest tests/test_pms.py

# With coverage
docker-compose exec hotel-whatsapp-bot python -m pytest --cov=.
```

### Debugging

```bash
# View environment variables
docker-compose exec hotel-whatsapp-bot env | grep GROQ

# Check Python packages
docker-compose exec hotel-whatsapp-bot pip list

# View process list
docker-compose exec hotel-whatsapp-bot ps aux

# Check network connectivity
docker-compose exec hotel-whatsapp-bot ping hotel-redis
```

## Production Deployment

### 1. Prepare Production Environment

```bash
# Create production .env
cp .env.example .env.production

# Edit with production values
nano .env.production
```

### 2. Optimize for Production

```yaml
# docker-compose.prod.yml
services:
  hotel-whatsapp-bot:
    environment:
      - FLASK_DEBUG=false
      - LOG_LEVEL=WARNING
      - GUNICORN_WORKERS=8
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 3. Deploy with Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml hotel-agent

# Check services
docker service ls

# Scale WhatsApp bot
docker service scale hotel-agent_hotel-whatsapp-bot=3

# View service logs
docker service logs -f hotel-agent_hotel-whatsapp-bot
```

### 4. Deploy with Kubernetes

Convert to K8s manifests:

```bash
# Install kompose
curl -L https://github.com/kubernetes/kompose/releases/download/v1.31.2/kompose-linux-amd64 -o kompose
chmod +x kompose
sudo mv kompose /usr/local/bin/

# Convert
kompose convert -f docker-compose.yml

# Deploy to K8s
kubectl apply -f .
```

## Cloud Deployment

### AWS ECS

```bash
# Install ECS CLI
sudo curl -Lo /usr/local/bin/ecs-cli https://amazon-ecs-cli.s3.amazonaws.com/ecs-cli-linux-amd64-latest
sudo chmod +x /usr/local/bin/ecs-cli

# Configure
ecs-cli configure --cluster hotel-agent --region us-east-1 --default-launch-type FARGATE

# Create cluster
ecs-cli up --cluster-config hotel-agent

# Deploy
ecs-cli compose --file docker-compose.yml up
```

### Google Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/hotel-whatsapp-bot

# Deploy
gcloud run deploy hotel-whatsapp-bot \
  --image gcr.io/PROJECT_ID/hotel-whatsapp-bot \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Azure Container Instances

```bash
# Create resource group
az group create --name hotel-agent --location eastus

# Create container
az container create \
  --resource-group hotel-agent \
  --name hotel-whatsapp-bot \
  --image your-registry/hotel-whatsapp-bot \
  --dns-name-label hotel-agent \
  --ports 5000 \
  --environment-variables GROQ_API_KEY=$GROQ_API_KEY
```

### DigitalOcean App Platform

```bash
# Install doctl
snap install doctl

# Create app
doctl apps create --spec .do/app.yaml

# Or use UI and connect to GitHub repo
```

## Monitoring and Logging

### Prometheus + Grafana

Add to docker-compose.yml:

```yaml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### Centralized Logging

```yaml
  # Add to services
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"

  # Or use ELK stack
  elasticsearch:
    image: elasticsearch:8.8.0

  logstash:
    image: logstash:8.8.0

  kibana:
    image: kibana:8.8.0
```

### Health Checks

```bash
# Manual health check
curl http://localhost:5000/health

# Automated monitoring
while true; do
  curl -s http://localhost:5000/health | jq '.status'
  sleep 30
done

# Use healthcheck in docker-compose (already configured)
```

## Backup and Recovery

### Backup Redis Data

```bash
# Trigger Redis save
docker-compose exec hotel-redis redis-cli BGSAVE

# Copy RDB file
docker cp hotel-redis:/data/dump.rdb ./backups/dump-$(date +%Y%m%d).rdb

# Backup with make
make backup-redis
```

### Restore Redis Data

```bash
# Stop services
docker-compose down

# Copy backup to volume
docker run --rm -v hotel-redis-data:/data -v $(pwd)/backups:/backup \
  alpine sh -c "cp /backup/dump.rdb /data/"

# Start services
docker-compose up -d
```

### Automated Backups

Create backup script:

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/redis"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
docker-compose exec -T hotel-redis redis-cli BGSAVE

# Wait for save to complete
sleep 5

# Copy backup
docker cp hotel-redis:/data/dump.rdb "$BACKUP_DIR/dump-$DATE.rdb"

# Keep only last 7 days
find $BACKUP_DIR -name "dump-*.rdb" -mtime +7 -delete

echo "Backup completed: dump-$DATE.rdb"
```

Add to cron:
```bash
# Run daily at 2 AM
0 2 * * * /path/to/backup.sh
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs hotel-whatsapp-bot

# Check container status
docker-compose ps

# Inspect container
docker inspect hotel-whatsapp-bot

# Check environment variables
docker-compose config
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose ps hotel-redis

# Test Redis connection
docker-compose exec hotel-redis redis-cli ping

# Check from app container
docker-compose exec hotel-whatsapp-bot nc -zv hotel-redis 6379
```

### Port Already in Use

```bash
# Find process using port
sudo lsof -i :5000

# Kill process
sudo kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "5001:5000"
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Limit memory in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1G

# Clear Docker cache
docker system prune -a
```

### Build Failures

```bash
# Clear build cache
docker-compose build --no-cache

# Pull fresh base images
docker pull python:3.11-slim

# Check disk space
df -h
```

## Performance Tuning

### Optimize Image Size

```dockerfile
# Use multi-stage build
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "whatsapp_bot.py"]
```

### Scale Workers

```bash
# Increase Gunicorn workers
environment:
  - GUNICORN_WORKERS=16

# Or use Docker replicas
docker-compose up -d --scale hotel-whatsapp-bot=3
```

### Use Redis Clustering

```yaml
  redis-master:
    image: redis:7-alpine

  redis-replica-1:
    image: redis:7-alpine
    command: redis-server --replicaof redis-master 6379

  redis-replica-2:
    image: redis:7-alpine
    command: redis-server --replicaof redis-master 6379
```

## Security Best Practices

### 1. Don't Commit Secrets

```bash
# Always use .env files
# Add to .gitignore
.env
.env.production
```

### 2. Use Docker Secrets (Swarm)

```bash
# Create secret
echo "my_groq_key" | docker secret create groq_api_key -

# Use in compose
secrets:
  groq_api_key:
    external: true

services:
  hotel-whatsapp-bot:
    secrets:
      - groq_api_key
```

### 3. Run as Non-Root

```dockerfile
# Add to Dockerfile
RUN useradd -m -u 1000 appuser
USER appuser
```

### 4. Scan Images

```bash
# Use Trivy
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image hotel-whatsapp-bot:latest
```

### 5. Network Isolation

```yaml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true

services:
  hotel-whatsapp-bot:
    networks:
      - frontend
      - backend
  hotel-redis:
    networks:
      - backend
```

## FAQ

**Q: Can I run without Docker?**
A: Yes, see HOW_TO_RUN.md for non-Docker setup.

**Q: How do I update to latest code?**
```bash
git pull
docker-compose build
docker-compose up -d
```

**Q: How much resources does it need?**
- WhatsApp bot: 512MB RAM, 0.5 CPU
- Voice agent: 1GB RAM, 1.0 CPU
- Redis: 256MB RAM, 0.25 CPU

**Q: Can I run on Raspberry Pi?**
A: Yes, but use ARM-compatible base images.

**Q: How do I enable HTTPS?**
A: Use Nginx reverse proxy or cloud load balancer.

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Verify environment: `docker-compose config`
3. Test connectivity: `docker-compose exec hotel-whatsapp-bot ping hotel-redis`
4. Check health: `make health`

## Resources

- Docker docs: https://docs.docker.com
- Docker Compose: https://docs.docker.com/compose/
- Best practices: https://docs.docker.com/develop/dev-best-practices/
