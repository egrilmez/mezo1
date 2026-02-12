.PHONY: help build up down restart logs clean test health

# Default target
help:
	@echo "Hotel Reservation Agent - Docker Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  help            Show this help message"
	@echo "  build           Build Docker images"
	@echo "  up              Start all services"
	@echo "  up-whatsapp     Start WhatsApp bot only"
	@echo "  up-voice        Start voice agent only"
	@echo "  down            Stop all services"
	@echo "  restart         Restart all services"
	@echo "  logs            View logs from all services"
	@echo "  logs-whatsapp   View WhatsApp bot logs"
	@echo "  logs-voice      View voice agent logs"
	@echo "  logs-redis      View Redis logs"
	@echo "  clean           Remove all containers and volumes"
	@echo "  test            Run tests"
	@echo "  health          Check service health"
	@echo "  shell-whatsapp  Open shell in WhatsApp bot container"
	@echo "  shell-redis     Open Redis CLI"

# Build all images
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d hotel-redis hotel-whatsapp-bot

# Start WhatsApp bot only
up-whatsapp:
	docker-compose up -d hotel-redis hotel-whatsapp-bot

# Start voice agent only (requires LiveKit credentials)
up-voice:
	docker-compose up -d hotel-voice-agent

# Start with voice agent profile
up-all:
	docker-compose --profile voice up -d

# Stop all services
down:
	docker-compose down

# Restart services
restart:
	docker-compose restart hotel-whatsapp-bot hotel-voice-agent

# View logs
logs:
	docker-compose logs -f hotel-whatsapp-bot hotel-voice-agent hotel-redis

# View WhatsApp bot logs
logs-whatsapp:
	docker-compose logs -f hotel-whatsapp-bot

# View voice agent logs
logs-voice:
	docker-compose logs -f hotel-voice-agent

# View Redis logs
logs-redis:
	docker-compose logs -f hotel-redis

# Clean everything
clean:
	docker-compose down -v
	docker system prune -f

# Run tests
test:
	docker-compose exec hotel-whatsapp-bot python -m pytest tests/

# Check service health
health:
	@echo "Checking service health..."
	@curl -s http://localhost:5000/health | python -m json.tool || echo "WhatsApp bot: Not responding"
	@docker-compose exec hotel-redis redis-cli ping || echo "Redis: Not responding"

# Open shell in WhatsApp bot container
shell-whatsapp:
	docker-compose exec hotel-whatsapp-bot /bin/bash

# Open Redis CLI
shell-redis:
	docker-compose exec hotel-redis redis-cli

# View container stats
stats:
	docker stats hotel-whatsapp-bot hotel-voice-agent hotel-redis

# Rebuild and restart
rebuild:
	docker-compose build hotel-whatsapp-bot hotel-voice-agent
	docker-compose up -d hotel-redis hotel-whatsapp-bot hotel-voice-agent

# Production deployment
deploy-prod:
	docker-compose --profile production up -d

# Backup Redis data
backup-redis:
	docker-compose exec hotel-redis redis-cli BGSAVE
	@echo "Redis backup initiated"

# Show running containers
ps:
	docker-compose ps
