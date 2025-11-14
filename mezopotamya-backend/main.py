# main.py - Simple MEZOPOTAMYA.TRAVEL Backend API
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import json
import requests
from datetime import datetime
import uvicorn

app = FastAPI(title="Mezopotamya.Travel API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
def init_db():
    conn = sqlite3.connect('mezopotamya.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS destinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            location TEXT,
            rating REAL,
            image_url TEXT,
            tags TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            message TEXT,
            response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            interests TEXT,
            visited_places TEXT,
            language TEXT DEFAULT 'tr'
        )
    ''')
    
    # Insert sample data
    sample_destinations = [
        ("Göbeklitepe", "Dünyanın en eski tapınak kompleksi, 12.000 yıllık tarih", "Tarihi", "Şanlıurfa", 4.8, "gobekli.jpg", "tarih,arkeoloji,unesco"),
        ("Balıklıgöl", "Hz. İbrahim'in ateşe atıldığı yer, kutsal göl", "Dini", "Şanlıurfa", 4.7, "balikligol.jpg", "din,tarih,göl"),
        ("Nemrut Dağı", "Kommagene Krallığı'nın dev heykelleri", "Tarihi", "Adıyaman", 4.9, "nemrut.jpg", "tarih,unesco,dağ"),
        ("Harran", "Koni evleriyle ünlü antik şehir", "Tarihi", "Şanlıurfa", 4.5, "harran.jpg", "tarih,mimari,antik"),
        ("Hasankeyf", "12.000 yıllık tarihi yerleşim", "Tarihi", "Batman", 4.6, "hasankeyf.jpg", "tarih,kale,höyük"),
        ("Mardin Kalesi", "Taş evleriyle ünlü tarihi şehir", "Tarihi", "Mardin", 4.7, "mardin.jpg", "tarih,mimari,kale"),
        ("Diyarbakır Surları", "Çin Seddi'nden sonra en uzun sur", "Tarihi", "Diyarbakır", 4.4, "sur.jpg", "tarih,sur,unesco"),
        ("Zeugma Mozaik Müzesi", "Dünyanın en büyük mozaik müzesi", "Müze", "Gaziantep", 4.8, "zeugma.jpg", "müze,mozaik,sanat")
    ]
    
    c.executemany('INSERT OR IGNORE INTO destinations (name, description, category, location, rating, image_url, tags) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                  sample_destinations)
    
    conn.commit()
    conn.close()

# Pydantic models
class ChatMessage(BaseModel):
    user_id: str
    message: str
    language: str = "tr"

class Destination(BaseModel):
    id: Optional[int]
    name: str
    description: str
    category: str
    location: str
    rating: float
    image_url: str
    tags: List[str]

class RecommendationRequest(BaseModel):
    user_id: str
    interests: List[str]
    max_results: int = 5

# Ollama LLM integration
def query_llm(prompt: str, model: str = "llama2"):
    """Query local Ollama instance"""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
        if response.status_code == 200:
            return response.json()['response']
        else:
            # Fallback to simple response if Ollama is not running
            return generate_simple_response(prompt)
    except:
        # Fallback response if Ollama is not available
        return generate_simple_response(prompt)

def generate_simple_response(prompt: str) -> str:
    """Simple rule-based fallback responses"""
    prompt_lower = prompt.lower()
    
    if "göbeklitepe" in prompt_lower:
        return "Göbeklitepe, dünyanın en eski tapınak kompleksidir. M.Ö. 10.000 yıllarına dayanan bu yapı, Şanlıurfa'da bulunur. UNESCO Dünya Mirası listesindedir."
    elif "otel" in prompt_lower or "konaklama" in prompt_lower:
        return "Bölgede birçok otel seçeneği bulunmaktadır. Şanlıurfa'da Hilton, Dedeman gibi büyük oteller var. Mardin'de butik taş evler popülerdir."
    elif "yemek" in prompt_lower or "ne yenir" in prompt_lower:
        return "GAP bölgesi zengin mutfağıyla ünlüdür. Urfa kebabı, çiğ köfte, Mardin'in kibe'si, Gaziantep baklavası mutlaka denenmeli lezzetlerdir."
    elif "ulaşım" in prompt_lower:
        return "Bölgeye havayolu ile Şanlıurfa, Gaziantep veya Diyarbakır havalimanlarından ulaşabilirsiniz. Şehirler arası otobüs seferleri de mevcuttur."
    else:
        return "GAP bölgesi, tarihi ve kültürel zenginlikleriyle sizi bekliyor. Size nasıl yardımcı olabilirim?"

# API Endpoints
@app.get("/")
def read_root():
    return {"message": "Mezopotamya.Travel API", "version": "1.0"}

@app.post("/chat")
def chat_endpoint(chat: ChatMessage):
    """AI Chat endpoint"""
    # Create context-aware prompt
    prompt = f"""Sen Mezopotamya bölgesi turizm asistanısın. Kullanıcı sorusu: {chat.message}
    
    Bölgedeki önemli yerler: Göbeklitepe, Balıklıgöl, Nemrut Dağı, Harran, Mardin, Hasankeyf.
    
    Kullanıcıya yardımcı ol, kısa ve öz cevap ver. Dil: {chat.language}"""
    
    response = query_llm(prompt)
    
    # Save conversation
    conn = sqlite3.connect('mezopotamya.db')
    c = conn.cursor()
    c.execute('INSERT INTO conversations (user_id, message, response) VALUES (?, ?, ?)',
              (chat.user_id, chat.message, response))
    conn.commit()
    conn.close()
    
    return {"response": response, "user_id": chat.user_id}

@app.get("/destinations")
def get_destinations(category: Optional[str] = None):
    """Get all destinations or filter by category"""
    conn = sqlite3.connect('mezopotamya.db')
    c = conn.cursor()
    
    if category:
        c.execute('SELECT * FROM destinations WHERE category = ?', (category,))
    else:
        c.execute('SELECT * FROM destinations')
    
    destinations = []
    for row in c.fetchall():
        destinations.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "category": row[3],
            "location": row[4],
            "rating": row[5],
            "image_url": row[6],
            "tags": row[7].split(',') if row[7] else []
        })
    
    conn.close()
    return destinations

@app.post("/recommendations")
def get_recommendations(request: RecommendationRequest):
    """Get personalized recommendations"""
    conn = sqlite3.connect('mezopotamya.db')
    c = conn.cursor()
    
    # Simple content-based filtering
    interests_str = ','.join(request.interests)
    query = f"""
        SELECT * FROM destinations 
        WHERE tags LIKE '%{interests_str}%' 
        ORDER BY rating DESC 
        LIMIT {request.max_results}
    """
    
    c.execute(query)
    recommendations = []
    for row in c.fetchall():
        recommendations.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "category": row[3],
            "location": row[4],
            "rating": row[5],
            "image_url": row[6],
            "tags": row[7].split(',') if row[7] else [],
            "match_score": 0.85  # Simple static score for now
        })
    
    conn.close()
    return {"recommendations": recommendations, "user_id": request.user_id}

@app.get("/destination/{destination_id}")
def get_destination_detail(destination_id: int):
    """Get detailed information about a destination"""
    conn = sqlite3.connect('mezopotamya.db')
    c = conn.cursor()
    c.execute('SELECT * FROM destinations WHERE id = ?', (destination_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "category": row[3],
        "location": row[4],
        "rating": row[5],
        "image_url": row[6],
        "tags": row[7].split(',') if row[7] else []
    }

@app.get("/chat/history/{user_id}")
def get_chat_history(user_id: str, limit: int = 10):
    """Get chat history for a user"""
    conn = sqlite3.connect('mezopotamya.db')
    c = conn.cursor()
    c.execute('''
        SELECT message, response, timestamp 
        FROM conversations 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (user_id, limit))
    
    history = []
    for row in c.fetchall():
        history.append({
            "message": row[0],
            "response": row[1],
            "timestamp": row[2]
        })
    
    conn.close()
    return {"user_id": user_id, "history": history}

if __name__ == "__main__":
    init_db()
    print("🚀 Mezopotamya.Travel API başlatılıyor...")
    print("📝 Veritabanı hazırlandı")
    print("🤖 LLM entegrasyonu: Ollama (localhost:11434)")
    print("🌐 API: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
