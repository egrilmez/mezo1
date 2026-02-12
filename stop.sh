#!/bin/bash

###############################################################################
# Hotel Reservation Agent - Stop Script
###############################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Hotel Reservation Agent - Stop Services              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

print_info "Stopping services..."
docker-compose down

echo ""
read -p "Do you want to remove data volumes? (y/N): " remove_volumes

if [[ $remove_volumes =~ ^[Yy]$ ]]; then
    print_warning "Removing volumes (all session data will be lost)..."
    docker-compose down -v
    print_success "Volumes removed"
else
    print_info "Volumes preserved"
fi

echo ""
print_success "All services stopped"
echo ""
