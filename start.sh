#!/bin/bash

###############################################################################
# Hotel Reservation Agent - Quick Start Script
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║     Hotel Reservation Agent - Docker Quick Start         ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_requirements() {
    print_info "Checking requirements..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_success "Docker is installed"

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    print_success "Docker Compose is installed"

    # Check if Docker daemon is running
    if ! docker ps &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    print_success "Docker daemon is running"
}

check_env_file() {
    print_info "Checking environment configuration..."

    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from .env.example..."
        cp .env.example .env
        print_success "Created .env file"
        echo ""
        print_warning "⚠️  IMPORTANT: Edit .env file with your API keys before proceeding!"
        echo ""
        echo "Required API keys:"
        echo "  • GROQ_API_KEY         - Get from https://groq.com"
        echo "  • TWILIO_ACCOUNT_SID   - Get from https://twilio.com"
        echo "  • TWILIO_AUTH_TOKEN    - Get from https://twilio.com"
        echo ""
        read -p "Press Enter after you've configured .env file..."
    else
        print_success ".env file exists"
    fi

    # Check for required variables
    if ! grep -q "GROQ_API_KEY=.*[^=]" .env 2>/dev/null; then
        print_warning "GROQ_API_KEY not set in .env"
    fi

    if ! grep -q "TWILIO_ACCOUNT_SID=.*[^=]" .env 2>/dev/null; then
        print_warning "TWILIO_ACCOUNT_SID not set in .env (required for WhatsApp)"
    fi
}

select_services() {
    echo ""
    print_info "Which services do you want to start?"
    echo ""
    echo "1) WhatsApp Bot only (text-based reservations)"
    echo "2) Voice Agent only (requires LiveKit setup)"
    echo "3) Both WhatsApp and Voice"
    echo "4) Exit"
    echo ""
    read -p "Select option (1-4): " choice

    case $choice in
        1)
            SERVICES="hotel-redis hotel-whatsapp-bot"
            SERVICE_NAME="WhatsApp Bot"
            ;;
        2)
            SERVICES="hotel-voice-agent"
            SERVICE_NAME="Voice Agent"
            # Check for LiveKit credentials
            if ! grep -q "LIVEKIT_URL=.*[^=]" .env 2>/dev/null; then
                print_error "LiveKit credentials not configured in .env"
                echo "Voice agent requires LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET"
                exit 1
            fi
            ;;
        3)
            SERVICES="hotel-redis hotel-whatsapp-bot hotel-voice-agent"
            SERVICE_NAME="All Services"
            ;;
        4)
            print_info "Exiting..."
            exit 0
            ;;
        *)
            print_error "Invalid option"
            exit 1
            ;;
    esac
}

build_images() {
    print_info "Building Docker images..."
    echo ""

    if docker-compose build; then
        print_success "Images built successfully"
    else
        print_error "Failed to build images"
        exit 1
    fi
}

start_services() {
    print_info "Starting $SERVICE_NAME..."
    echo ""

    if docker-compose up -d $SERVICES; then
        print_success "Services started successfully"
    else
        print_error "Failed to start services"
        exit 1
    fi
}

wait_for_services() {
    print_info "Waiting for services to be healthy..."

    # Wait for Redis
    if [[ $SERVICES == *"hotel-redis"* ]]; then
        for i in {1..30}; do
            if docker-compose exec -T hotel-redis redis-cli ping &> /dev/null; then
                print_success "Redis is ready"
                break
            fi
            if [ $i -eq 30 ]; then
                print_error "Redis failed to start"
                return 1
            fi
            sleep 1
        done
    fi

    # Wait for WhatsApp bot
    if [[ $SERVICES == *"hotel-whatsapp-bot"* ]]; then
        for i in {1..60}; do
            if curl -s http://localhost:5000/health &> /dev/null; then
                print_success "WhatsApp bot is ready"
                break
            fi
            if [ $i -eq 60 ]; then
                print_error "WhatsApp bot failed to start"
                return 1
            fi
            sleep 1
        done
    fi
}

show_status() {
    echo ""
    print_header
    print_success "Services are running!"
    echo ""

    # Show running containers
    print_info "Running containers:"
    docker-compose ps
    echo ""

    # Show access information
    if [[ $SERVICES == *"hotel-whatsapp-bot"* ]]; then
        echo "📱 WhatsApp Bot:"
        echo "   • Health check: http://localhost:5000/health"
        echo "   • Webhook: http://localhost:5000/webhook/whatsapp"
        echo "   • Configure this webhook URL in Twilio Console"
        echo ""
    fi

    if [[ $SERVICES == *"hotel-voice-agent"* ]]; then
        echo "🎤 Voice Agent:"
        echo "   • Connected to LiveKit"
        echo "   • Waiting for calls..."
        echo ""
    fi

    # Next steps
    print_info "Next steps:"
    echo ""

    if [[ $SERVICES == *"hotel-whatsapp-bot"* ]]; then
        echo "For WhatsApp:"
        echo "  1. Install ngrok: https://ngrok.com"
        echo "  2. Run: ngrok http 5000"
        echo "  3. Copy the HTTPS URL"
        echo "  4. Configure webhook in Twilio Console"
        echo "  5. Send a WhatsApp message to your Twilio number"
        echo ""
    fi

    echo "Useful commands:"
    echo "  • View logs:        make logs-whatsapp"
    echo "  • Check health:     make health"
    echo "  • Stop services:    make down"
    echo "  • Restart:          make restart"
    echo ""

    print_info "View logs in real-time:"
    echo "  docker-compose logs -f"
    echo ""
}

# Main script
main() {
    print_header

    check_requirements
    echo ""

    check_env_file
    echo ""

    select_services
    echo ""

    build_images
    echo ""

    start_services
    echo ""

    wait_for_services

    show_status
}

# Run main function
main
