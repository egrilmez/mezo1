"""
RAG (Retrieval-Augmented Generation) Service
Integrates Qdrant vector search with Ollama LLM for enhanced responses
"""

import os
from typing import List, Dict, Optional
from document_processor import DocumentProcessor
from vector_store import VectorStore
import requests


class RAGService:
    """RAG service combining vector search and LLM generation"""
    
    def __init__(self, vector_store: VectorStore = None, document_processor: DocumentProcessor = None):
        """
        Initialize RAG service
        
        Args:
            vector_store: VectorStore instance
            document_processor: DocumentProcessor instance
        """
        self.vector_store = vector_store or VectorStore()
        self.document_processor = document_processor or DocumentProcessor()
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    def query_llm(self, prompt: str, model: str = "llama2") -> str:
        """
        Query Ollama LLM
        
        Args:
            prompt: Prompt text
            model: Model name
            
        Returns:
            LLM response
        """
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                return self._generate_fallback_response(prompt)
        except Exception as e:
            print(f"Error querying LLM: {e}")
            return self._generate_fallback_response(prompt)
    
    def _generate_fallback_response(self, prompt: str) -> str:
        """Fallback response if LLM is unavailable"""
        return "Üzgünüm, şu anda AI servisi kullanılamıyor. Lütfen daha sonra tekrar deneyin."
    
    def retrieve_context(self, query: str, top_k: int = 5, 
                        filter_dict: Dict = None) -> List[Dict]:
        """
        Retrieve relevant context from vector store
        
        Args:
            query: User query
            top_k: Number of chunks to retrieve
            filter_dict: Optional metadata filters
            
        Returns:
            List of relevant chunks with metadata
        """
        # Generate query embedding
        query_embedding = self.document_processor.embed_text(query)
        
        # Search vector store
        results = self.vector_store.search(
            query_vector=query_embedding,
            limit=top_k,
            filter_dict=filter_dict
        )
        
        return results
    
    def format_context(self, results: List[Dict]) -> str:
        """
        Format retrieved context for LLM prompt
        
        Args:
            results: List of search results
            
        Returns:
            Formatted context string
        """
        if not results:
            return ""
        
        context_parts = []
        for i, result in enumerate(results, 1):
            text = result.get('text', '')
            metadata = result.get('metadata', {})
            title = metadata.get('title', 'Bilinmeyen Kaynak')
            
            context_parts.append(
                f"[Kaynak {i}: {title}]\n{text}\n"
            )
        
        return "\n".join(context_parts)
    
    def query(self, user_query: str, language: str = "tr", 
             top_k: int = 5, filter_dict: Dict = None,
             model: str = "llama2") -> Dict:
        """
        Perform RAG query: retrieve context and generate response
        
        Args:
            user_query: User's question
            language: Response language (tr/en)
            top_k: Number of context chunks to retrieve
            filter_dict: Optional metadata filters
            model: LLM model name
            
        Returns:
            Dictionary with response and retrieved context
        """
        # Retrieve relevant context
        context_results = self.retrieve_context(
            user_query, 
            top_k=top_k,
            filter_dict=filter_dict
        )
        
        # Format context
        context_text = self.format_context(context_results)
        
        # Build prompt with context
        if language == "tr":
            prompt = f"""Sen Mezopotamya bölgesi turizm asistanısın. Aşağıdaki bilgileri kullanarak kullanıcının sorusuna cevap ver.

İlgili Bilgiler:
{context_text if context_text else "Genel turizm bilgisi"}

Kullanıcı Sorusu: {user_query}

Kısa, öz ve yardımcı bir cevap ver. Sadece verilen bilgilere dayanarak cevap ver."""
        else:
            prompt = f"""You are a tourism assistant for the Mesopotamia region. Use the following information to answer the user's question.

Relevant Information:
{context_text if context_text else "General tourism information"}

User Question: {user_query}

Provide a short, concise, and helpful answer. Base your answer only on the provided information."""
        
        # Generate response using LLM
        response = self.query_llm(prompt, model=model)
        
        return {
            'response': response,
            'context': context_results,
            'context_count': len(context_results)
        }
    
    def generate_itinerary(self, preferences: Dict, language: str = "tr") -> Dict:
        """
        Generate tourism itinerary using RAG
        
        Args:
            preferences: User preferences (interests, duration, locations, etc.)
            language: Response language
            
        Returns:
            Generated itinerary with route suggestions
        """
        # Build query from preferences
        interests = preferences.get('interests', [])
        duration = preferences.get('duration', '3 gün')
        locations = preferences.get('locations', [])
        
        query_parts = [f"{duration} süreli bir tur planı"]
        if interests:
            query_parts.append(f"ilgi alanları: {', '.join(interests)}")
        if locations:
            query_parts.append(f"ziyaret edilecek yerler: {', '.join(locations)}")
        
        query = " ".join(query_parts)
        
        # Retrieve relevant itinerary and route information
        filter_dict = {'type': 'itinerary'} if 'itinerary' in str(preferences) else None
        context_results = self.retrieve_context(query, top_k=10, filter_dict=filter_dict)
        
        # Format context
        context_text = self.format_context(context_results)
        
        # Generate itinerary prompt
        if language == "tr":
            prompt = f"""Aşağıdaki turizm bilgilerini kullanarak detaylı bir tur planı oluştur.

Kullanıcı Tercihleri:
- Süre: {duration}
- İlgi Alanları: {', '.join(interests) if interests else 'Genel'}
- Lokasyonlar: {', '.join(locations) if locations else 'GAP Bölgesi'}

İlgili Bilgiler:
{context_text if context_text else "GAP bölgesi turizm bilgileri"}

Günlük program, önerilen rotalar, ziyaret yerleri ve pratik bilgiler içeren detaylı bir plan oluştur."""
        else:
            prompt = f"""Create a detailed travel itinerary using the following tourism information.

User Preferences:
- Duration: {duration}
- Interests: {', '.join(interests) if interests else 'General'}
- Locations: {', '.join(locations) if locations else 'GAP Region'}

Relevant Information:
{context_text if context_text else "GAP region tourism information"}

Create a detailed plan including daily schedule, recommended routes, places to visit, and practical information."""
        
        response = self.query_llm(prompt, model="llama2")
        
        return {
            'itinerary': response,
            'preferences': preferences,
            'context_sources': [r.get('metadata', {}).get('title', '') for r in context_results]
        }
    
    def generate_route(self, start_location: str, end_location: str, 
                      waypoints: List[str] = None, language: str = "tr") -> Dict:
        """
        Generate route between locations using RAG
        
        Args:
            start_location: Starting location
            end_location: Destination location
            waypoints: Optional waypoints
            language: Response language
            
        Returns:
            Generated route information
        """
        query = f"{start_location} ile {end_location} arası rota"
        if waypoints:
            query += f" üzerinden {', '.join(waypoints)}"
        
        # Retrieve relevant route information
        filter_dict = {'type': 'route'} if 'route' in str(waypoints) else None
        context_results = self.retrieve_context(query, top_k=8, filter_dict=filter_dict)
        
        context_text = self.format_context(context_results)
        
        # Generate route prompt
        if language == "tr":
            prompt = f"""Aşağıdaki bilgileri kullanarak detaylı bir rota planı oluştur.

Rota Bilgileri:
- Başlangıç: {start_location}
- Varış: {end_location}
- Ara Duraklar: {', '.join(waypoints) if waypoints else 'Yok'}

İlgili Bilgiler:
{context_text if context_text else "GAP bölgesi ulaşım bilgileri"}

Mesafe, süre, yol durumu, önemli noktalar ve pratik bilgiler içeren detaylı bir rota oluştur."""
        else:
            prompt = f"""Create a detailed route plan using the following information.

Route Information:
- Start: {start_location}
- Destination: {end_location}
- Waypoints: {', '.join(waypoints) if waypoints else 'None'}

Relevant Information:
{context_text if context_text else "GAP region transportation information"}

Create a detailed route including distance, duration, road conditions, important points, and practical information."""
        
        response = self.query_llm(prompt, model="llama2")
        
        return {
            'route': response,
            'start_location': start_location,
            'end_location': end_location,
            'waypoints': waypoints or [],
            'context_sources': [r.get('metadata', {}).get('title', '') for r in context_results]
        }

