#!/bin/bash

# MEZOPOTAMYA.TRAVEL - Quick Setup Script
# =========================================

echo "🏛️ MEZOPOTAMYA.TRAVEL Platform Kurulumu"
echo "========================================"

# Check dependencies
check_dependency() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 bulunamadı. Lütfen $2"
        exit 1
    fi
    echo "✅ $1 mevcut"
}

echo "📋 Bağımlılıklar kontrol ediliyor..."
check_dependency "python3" "Python 3.9+ yükleyin"
check_dependency "node" "Node.js 18+ yükleyin"
check_dependency "docker" "Docker yükleyin"

# Setup options
echo ""
echo "Kurulum seçenekleri:"
echo "1) Docker ile kurulum (Önerilen)"
echo "2) Manuel kurulum"
echo "3) Sadece Ollama kurulumu"
read -p "Seçiminiz (1-3): " choice

case $choice in
    1)
        echo "🐳 Docker ile kuruluyor..."
        
        # Create necessary directories
        mkdir -p data
        mkdir -p mezopotamya-backend
        mkdir -p mezopotamya-frontend/pages
        
        # Start Docker Compose
        docker-compose up -d
        
        echo "✅ Kurulum tamamlandı!"
        echo "📱 Frontend: http://localhost:3000"
        echo "🔧 Backend API: http://localhost:8000"
        echo "🤖 Ollama: http://localhost:11434"
        ;;
        
    2)
        echo "🔧 Manuel kurulum başlatılıyor..."
        
        # Backend setup
        echo "📦 Backend kurulumu..."
        cd mezopotamya-backend
        pip3 install -r requirements.txt
        
        # Start backend in background
        echo "🚀 Backend başlatılıyor..."
        python3 main.py &
        BACKEND_PID=$!
        
        cd ..
        
        # Frontend setup
        echo "📦 Frontend kurulumu..."
        cd mezopotamya-frontend
        npm install
        
        # Create next.config.js
        cat > next.config.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    API_URL: process.env.API_URL || 'http://localhost:8000',
  },
}

module.exports = nextConfig
EOF
        
        # Start frontend
        echo "🚀 Frontend başlatılıyor..."
        npm run dev &
        FRONTEND_PID=$!
        
        cd ..
        
        echo "✅ Manuel kurulum tamamlandı!"
        echo "📱 Frontend: http://localhost:3000"
        echo "🔧 Backend API: http://localhost:8000"
        echo ""
        echo "⚠️  Ollama'yı ayrıca kurmanız gerekiyor:"
        echo "curl -fsSL https://ollama.ai/install.sh | sh"
        echo "ollama serve"
        echo "ollama pull llama2:7b-chat"
        
        # Wait for user input to stop
        read -p "Durdurmak için Enter'a basın..."
        kill $BACKEND_PID $FRONTEND_PID
        ;;
        
    3)
        echo "🤖 Ollama kurulumu..."
        
        # Install Ollama
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            curl -fsSL https://ollama.ai/install.sh | sh
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            echo "MacOS için: https://ollama.ai/download adresinden indirin"
        else
            echo "Windows için: https://ollama.ai/download adresinden indirin"
        fi
        
        # Start Ollama
        ollama serve &
        sleep 5
        
        # Pull models
        echo "📥 Modeller indiriliyor..."
        ollama pull llama2:7b-chat
        ollama pull mistral:7b-instruct
        
        echo "✅ Ollama kurulumu tamamlandı!"
        echo "Test etmek için: curl http://localhost:11434/api/generate -d '{\"model\":\"llama2\",\"prompt\":\"Merhaba\"}'"
        ;;
        
    *)
        echo "Geçersiz seçim"
        exit 1
        ;;
esac

echo ""
echo "🎉 Kurulum başarılı!"
echo "📚 Dokümantasyon için README.md dosyasını okuyun"
