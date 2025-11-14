# 🚀 MEZOPOTAMYA.TRAVEL - HIZLI BAŞLANGIÇ

## 5 Dakikada Çalıştırın!

### Opsiyon 1: Tek Komutla Kurulum (Önerilen)

```bash
# Setup scriptini çalıştırın
chmod +x setup.sh
./setup.sh

# 1'i seçin (Docker kurulumu)
```

### Opsiyon 2: Manuel Hızlı Kurulum

#### 1️⃣ Ollama Kurulumu (2 dakika)
```bash
# Mac/Linux için
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve &
ollama pull llama2:7b-chat
```

#### 2️⃣ Backend Başlatma (1 dakika)
```bash
cd mezopotamya-backend
pip3 install fastapi uvicorn requests
python3 main.py &
```

#### 3️⃣ Frontend Başlatma (2 dakika)
```bash
cd mezopotamya-frontend
npm install
npm run dev
```

## ✅ Kurulum Tamamlandı!

🌐 **Frontend**: http://localhost:3000
🔧 **API**: http://localhost:8000
📊 **Admin Panel**: http://localhost:3000/admin

## 🎯 İlk Adımlar

### 1. Chat'i Test Edin
- Frontend'i açın: http://localhost:3000
- "Göbeklitepe hakkında bilgi" yazın
- AI asistanın cevabını görün

### 2. API'yi Test Edin
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "Merhaba", "language": "tr"}'
```

### 3. Admin Panel
- http://localhost:3000/admin adresine gidin
- Destinasyonları görüntüleyin
- Sohbet geçmişini inceleyin
- Yeni destinasyon ekleyin

## 🛠️ Sorun Giderme

### Ollama çalışmıyor
```bash
# Servisi yeniden başlatın
killall ollama
ollama serve &
```

### Port kullanımda
```bash
# 8000 portu kullanılıyorsa
lsof -i :8000
kill -9 [PID]

# 3000 portu kullanılıyorsa
lsof -i :3000
kill -9 [PID]
```

### Database hatası
```bash
# Database'i sıfırlayın
rm mezopotamya.db
python3 main.py  # Yeniden oluşturur
```

## 📱 Mobil Test

Telefonunuzdan test etmek için:
1. Bilgisayar IP'nizi bulun: `ipconfig` veya `ifconfig`
2. Telefonda açın: `http://[BILGISAYAR_IP]:3000`

## 🔥 Hızlı Demo Verileri

```python
# Demo destinasyon eklemek için
import requests

destinations = [
    {
        "name": "Halfeti",
        "description": "Kara gülleriyle ünlü",
        "category": "Doğa",
        "location": "Şanlıurfa",
        "rating": 4.7
    },
    {
        "name": "Dara Antik Kenti",
        "description": "Mezopotamya'nın Efes'i",
        "category": "Tarihi",
        "location": "Mardin",
        "rating": 4.6
    }
]

for dest in destinations:
    requests.post("http://localhost:8000/destinations", json=dest)
```

## 📞 Destek

Sorun yaşıyorsanız:
1. README.md dosyasını kontrol edin
2. Log dosyalarını inceleyin
3. Docker logs: `docker-compose logs`

## ✨ Sonraki Adımlar

1. **Güvenlik**: Production için SSL ekleyin
2. **Performans**: Redis cache ekleyin
3. **Özellikler**: WhatsApp entegrasyonu
4. **Deployment**: Cloud'a taşıyın

---

🎉 **Tebrikler! Platform hazır!**
