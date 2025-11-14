# 🏛️ MEZOPOTAMYA.TRAVEL - Turizm AI Asistan Platformu

## 📖 Proje Hakkında

Mezopotamya.Travel, GAP bölgesi turizmi için geliştirilmiş yapay zeka destekli bir turizm asistan platformudur. Turistlere kişiselleştirilmiş öneriler, anlık sohbet desteği ve kapsamlı bölge bilgisi sunar.

## 🚀 Özellikler

### ✅ Mevcut Özellikler
- **AI Sohbet Asistanı**: Türkçe ve İngilizce dil desteği
- **Kişiselleştirilmiş Öneriler**: İlgi alanlarına göre destinasyon önerileri
- **Destinasyon Veritabanı**: GAP bölgesi turistik yerleri
- **Kullanıcı Takibi**: Sohbet geçmişi ve tercihler
- **In-House LLM**: Ollama ile yerelde çalışan AI modeli
- **Modern Web Arayüzü**: Responsive tasarım

### 🔄 Geliştirme Aşamasında
- WhatsApp entegrasyonu
- Gelişmiş öneri algoritmaları
- İnteraktif haritalar
- Çoklu dil desteği (Arapça, Kürtçe)
- Ödeme sistemi entegrasyonu

## 🛠️ Teknoloji Stack

### Backend
- **Python 3.11** + **FastAPI**: Hızlı ve modern API
- **SQLite**: Hafif veritabanı (production için PostgreSQL'e geçilebilir)
- **Ollama**: Yerelde çalışan LLM (Llama 2, Mistral)

### Frontend
- **Next.js 14**: React tabanlı modern framework
- **TypeScript**: Type-safe geliştirme
- **Tailwind CSS**: Utility-first CSS

### AI/ML
- **Ollama**: In-house LLM hosting
- **Llama 2 7B**: Sohbet modeli
- **Content-Based Filtering**: Öneri sistemi

## 📦 Kurulum

### Hızlı Kurulum (Docker)

```bash
# Repository'yi klonla
git clone [repo-url]
cd mezopotamya-travel

# Docker ile başlat
docker-compose up -d

# Servisleri kontrol et
docker-compose ps
```

### Manuel Kurulum

#### 1. Ollama Kurulumu
```bash
# Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh

# Modelleri indir
ollama pull llama2:7b-chat
ollama pull mistral:7b-instruct

# Servisi başlat
ollama serve
```

#### 2. Backend Kurulumu
```bash
cd mezopotamya-backend
pip install -r requirements.txt
python main.py
```

#### 3. Frontend Kurulumu
```bash
cd mezopotamya-frontend
npm install
npm run dev
```

## 🔧 Yapılandırma

### Ortam Değişkenleri

Backend (`.env`):
```
DATABASE_PATH=./mezopotamya.db
OLLAMA_HOST=http://localhost:11434
API_PORT=8000
```

Frontend (`.env.local`):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🌐 API Endpoints

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/chat` | POST | AI ile sohbet |
| `/destinations` | GET | Tüm destinasyonları listele |
| `/recommendations` | POST | Kişiselleştirilmiş öneriler |
| `/destination/{id}` | GET | Destinasyon detayı |
| `/chat/history/{user_id}` | GET | Sohbet geçmişi |

### Örnek API Kullanımı

```python
import requests

# Sohbet
response = requests.post("http://localhost:8000/chat", json={
    "user_id": "user123",
    "message": "Göbeklitepe hakkında bilgi verir misin?",
    "language": "tr"
})

# Öneriler
response = requests.post("http://localhost:8000/recommendations", json={
    "user_id": "user123",
    "interests": ["tarih", "arkeoloji"],
    "max_results": 5
})
```

## 📊 Veritabanı Şeması

```sql
-- Destinasyonlar
CREATE TABLE destinations (
    id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT,
    category TEXT,
    location TEXT,
    rating REAL,
    image_url TEXT,
    tags TEXT
);

-- Konuşmalar
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    message TEXT,
    response TEXT,
    timestamp DATETIME
);

-- Kullanıcı Tercihleri
CREATE TABLE user_preferences (
    user_id TEXT PRIMARY KEY,
    interests TEXT,
    visited_places TEXT,
    language TEXT
);
```

## 🧪 Test

```bash
# Backend testleri
cd mezopotamya-backend
pytest tests/

# Frontend testleri
cd mezopotamya-frontend
npm test
```

## 📈 Performans

- **Yanıt Süresi**: <2 saniye (lokal LLM)
- **Concurrent Users**: 100+
- **Memory Usage**: ~2GB (LLM dahil)
- **Database Size**: <100MB (10K kayıt)

## 🚀 Production Deployment

### 1. Güvenlik
- SSL sertifikası ekle
- API rate limiting
- Input validation
- CORS yapılandırması

### 2. Ölçeklendirme
- PostgreSQL'e geç
- Redis cache ekle
- Load balancer kullan
- CDN entegrasyonu

### 3. Monitoring
- Application monitoring (Prometheus)
- Error tracking (Sentry)
- Analytics (Google Analytics)
- Uptime monitoring

## 📝 Yol Haritası

### Q1 2025
- [x] MVP geliştirme
- [x] Temel AI sohbet
- [x] Basit öneri sistemi
- [ ] Beta test

### Q2 2025
- [ ] WhatsApp entegrasyonu
- [ ] Gelişmiş ML modelleri
- [ ] İnteraktif haritalar
- [ ] Mobil uygulama

### Q3 2025
- [ ] Ödeme sistemi
- [ ] Rezervasyon entegrasyonu
- [ ] Çoklu dil (5+ dil)
- [ ] B2B portal

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing`)
5. Pull Request açın

## 📞 İletişim

- **Proje Sahibi**: AGENTİC DYNAMİC YAZILIM
- **Email**: info@mezopotamya.travel
- **Website**: https://mezopotamya.travel

## 📄 Lisans

Bu proje AGENTİC DYNAMİC YAZILIM tarafından GAP İdaresi için geliştirilmiştir.

---

**Not**: Bu bir MVP (Minimum Viable Product) versiyonudur. Production kullanımı için güvenlik, performans ve ölçeklendirme optimizasyonları gereklidir.
