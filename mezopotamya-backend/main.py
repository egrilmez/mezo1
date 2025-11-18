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
import os

# Import RAG modules
from document_processor import DocumentProcessor
from vector_store import VectorStore
from rag_service import RAGService

app = FastAPI(title="Mezopotamya.Travel API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG components
vector_store = None
document_processor = None
rag_service = None

# Database helper
def get_db_connection():
    """Get database connection using configured path"""
    db_path = os.getenv("DATABASE_PATH", "mezopotamya.db")
    return sqlite3.connect(db_path)

# Database setup
def init_db():
    global vector_store, document_processor, rag_service
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create existing tables
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
    
    # New tables for RAG functionality
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            type TEXT,
            source TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            chunk_text TEXT,
            chunk_index INTEGER,
            vector_id TEXT,
            FOREIGN KEY (document_id) REFERENCES documents(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS itineraries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            route_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            waypoints TEXT,
            distance REAL,
            duration TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
    
    # Initialize Qdrant and RAG services
    try:
        vector_store = VectorStore()
        if vector_store.is_connected():
            vector_store.ensure_collection(vector_size=384)
            print("✅ Qdrant bağlantısı başarılı")
        else:
            print("⚠️ Qdrant bağlantısı başarısız, RAG özellikleri devre dışı")
    except Exception as e:
        print(f"⚠️ Qdrant başlatma hatası: {e}")
        vector_store = None
    
    # Initialize document processor
    try:
        chunk_size = int(os.getenv("CHUNK_SIZE", "512"))
        chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "50"))
        document_processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        print("✅ Document processor hazır")
    except Exception as e:
        print(f"⚠️ Document processor başlatma hatası: {e}")
        document_processor = None
    
    # Initialize RAG service
    if vector_store and document_processor:
        try:
            rag_service = RAGService(vector_store=vector_store, document_processor=document_processor)
            print("✅ RAG servisi hazır")
        except Exception as e:
            print(f"⚠️ RAG servisi başlatma hatası: {e}")
            rag_service = None

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

class DocumentIngestRequest(BaseModel):
    title: str
    content: str
    type: str = "general"  # itinerary, route, destination_info, general
    source: Optional[str] = None

class DocumentSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    filter_type: Optional[str] = None

class ItineraryRequest(BaseModel):
    interests: List[str]
    duration: str = "3 gün"
    locations: Optional[List[str]] = None
    language: str = "tr"

class RouteRequest(BaseModel):
    start_location: str
    end_location: str
    waypoints: Optional[List[str]] = None
    language: str = "tr"

# Ollama LLM integration
def query_llm(prompt: str, model: str = "llama2"):
    """Query local Ollama instance"""
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        response = requests.post(
            f"{ollama_host}/api/generate",
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
    """AI Chat endpoint with RAG support"""
    # Use RAG service if available, otherwise fallback to basic LLM
    if rag_service:
        try:
            result = rag_service.query(
                user_query=chat.message,
                language=chat.language,
                top_k=5
            )
            response = result['response']
        except Exception as e:
            print(f"RAG query error: {e}")
            # Fallback to basic LLM
            prompt = f"""Sen Mezopotamya bölgesi turizm asistanısın. Kullanıcı sorusu: {chat.message}
    
    Bölgedeki önemli yerler: Göbeklitepe, Balıklıgöl, Nemrut Dağı, Harran, Mardin, Hasankeyf.
    
    Kullanıcıya yardımcı ol, kısa ve öz cevap ver. Dil: {chat.language}"""
            response = query_llm(prompt)
    else:
        # Fallback to basic LLM
        prompt = f"""Sen Mezopotamya bölgesi turizm asistanısın. Kullanıcı sorusu: {chat.message}
    
    Bölgedeki önemli yerler: Göbeklitepe, Balıklıgöl, Nemrut Dağı, Harran, Mardin, Hasankeyf.
    
    Kullanıcıya yardımcı ol, kısa ve öz cevap ver. Dil: {chat.language}"""
        response = query_llm(prompt)
    
    # Save conversation
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO conversations (user_id, message, response) VALUES (?, ?, ?)',
              (chat.user_id, chat.message, response))
    conn.commit()
    conn.close()
    
    return {"response": response, "user_id": chat.user_id}

@app.get("/destinations")
def get_destinations(category: Optional[str] = None):
    """Get all destinations or filter by category"""
    conn = get_db_connection()
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
    conn = get_db_connection()
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
    conn = get_db_connection()
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
    conn = get_db_connection()
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

# RAG and Document Management Endpoints
@app.post("/documents/ingest")
def ingest_document(doc: DocumentIngestRequest):
    """Ingest and process a document for RAG"""
    if not document_processor or not vector_store:
        raise HTTPException(status_code=503, detail="Document processing service unavailable")
    
    try:
        # Process document
        processed = document_processor.process_document(
            text=doc.content,
            title=doc.title,
            doc_type=doc.type,
            source=doc.source
        )
        
        # Generate embeddings for chunks
        chunks_with_embeddings = document_processor.embed_chunks(processed['chunks'])
        
        # Save document to database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO documents (title, content, type, source)
            VALUES (?, ?, ?, ?)
        ''', (doc.title, doc.content, doc.type, doc.source))
        document_id = c.lastrowid
        
        # Save chunks to database and Qdrant
        vector_ids = []
        for chunk in chunks_with_embeddings:
            vector_id = f"{document_id}_{chunk['chunk_index']}"
            chunk['vector_id'] = vector_id
            vector_ids.append(vector_id)
            
            c.execute('''
                INSERT INTO document_chunks (document_id, chunk_text, chunk_index, vector_id)
                VALUES (?, ?, ?, ?)
            ''', (document_id, chunk['text'], chunk['chunk_index'], vector_id))
        
        conn.commit()
        conn.close()
        
        # Add to Qdrant
        vector_store.add_documents(chunks_with_embeddings, document_id=document_id)
        
        return {
            "document_id": document_id,
            "title": doc.title,
            "chunks_created": len(chunks_with_embeddings),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ingesting document: {str(e)}")

@app.post("/documents/search")
def search_documents(search: DocumentSearchRequest):
    """Semantic search in document corpus"""
    if not document_processor or not vector_store:
        raise HTTPException(status_code=503, detail="Search service unavailable")
    
    try:
        # Generate query embedding
        query_embedding = document_processor.embed_text(search.query)
        
        # Build filter
        filter_dict = None
        if search.filter_type:
            filter_dict = {'type': search.filter_type}
        
        # Search Qdrant
        results = vector_store.search(
            query_vector=query_embedding,
            limit=search.top_k,
            filter_dict=filter_dict
        )
        
        return {
            "query": search.query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching documents: {str(e)}")

@app.get("/documents")
def list_documents(limit: int = 20, offset: int = 0):
    """List ingested documents"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, title, type, source, created_at
        FROM documents
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    
    documents = []
    for row in c.fetchall():
        documents.append({
            "id": row[0],
            "title": row[1],
            "type": row[2],
            "source": row[3],
            "created_at": row[4]
        })
    
    conn.close()
    return {"documents": documents, "count": len(documents)}

@app.delete("/documents/{doc_id}")
def delete_document(doc_id: int):
    """Delete a document and its vectors"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store unavailable")
    
    try:
        # Delete from Qdrant
        vector_store.delete_document(doc_id)
        
        # Delete from database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM document_chunks WHERE document_id = ?', (doc_id,))
        c.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
        conn.commit()
        conn.close()
        
        return {"document_id": doc_id, "status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@app.post("/itineraries/generate")
def generate_itinerary(request: ItineraryRequest):
    """Generate tourism itinerary using RAG"""
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service unavailable")
    
    try:
        preferences = {
            'interests': request.interests,
            'duration': request.duration,
            'locations': request.locations or []
        }
        
        result = rag_service.generate_itinerary(
            preferences=preferences,
            language=request.language
        )
        
        # Save itinerary to database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO itineraries (name, description, route_data)
            VALUES (?, ?, ?)
        ''', (
            f"Plan - {request.duration}",
            result['itinerary'],
            json.dumps(preferences)
        ))
        itinerary_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "itinerary_id": itinerary_id,
            "itinerary": result['itinerary'],
            "preferences": preferences,
            "sources": result.get('context_sources', [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating itinerary: {str(e)}")

@app.post("/routes/generate")
def generate_route(request: RouteRequest):
    """Generate route between locations using RAG"""
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service unavailable")
    
    try:
        result = rag_service.generate_route(
            start_location=request.start_location,
            end_location=request.end_location,
            waypoints=request.waypoints,
            language=request.language
        )
        
        # Save route to database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO routes (name, waypoints, distance, duration)
            VALUES (?, ?, ?, ?)
        ''', (
            f"{request.start_location} - {request.end_location}",
            json.dumps(request.waypoints or []),
            0.0,  # Distance would be calculated separately
            "N/A"  # Duration would be calculated separately
        ))
        route_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "route_id": route_id,
            "route": result['route'],
            "start_location": result['start_location'],
            "end_location": result['end_location'],
            "waypoints": result['waypoints'],
            "sources": result.get('context_sources', [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating route: {str(e)}")

@app.get("/qdrant/status")
def get_qdrant_status():
    """Get Qdrant connection status and collection info"""
    if not vector_store:
        return {"connected": False, "message": "Vector store not initialized"}
    
    if not vector_store.is_connected():
        return {"connected": False, "message": "Cannot connect to Qdrant"}
    
    info = vector_store.get_collection_info()
    return {
        "connected": True,
        "collection": info
    }

if __name__ == "__main__":
    init_db()
    print("🚀 Mezopotamya.Travel API başlatılıyor...")
    print("📝 Veritabanı hazırlandı")
    print("🤖 LLM entegrasyonu: Ollama")
    if vector_store and vector_store.is_connected():
        print("🔍 Qdrant vektör veritabanı: Bağlı")
    else:
        print("⚠️ Qdrant vektör veritabanı: Bağlantı yok")
    if rag_service:
        print("🧠 RAG servisi: Aktif")
    else:
        print("⚠️ RAG servisi: Devre dışı")
    print("🌐 API: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
