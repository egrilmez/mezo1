"""
Document Processing Module for Semantic Chunking
Handles document chunking, metadata extraction, and text preprocessing
for Turkish and English tourism documents.
"""

import os
import re
from typing import List, Dict, Optional, Tuple
from sentence_transformers import SentenceTransformer
import tiktoken

# Initialize tokenizer for chunk size calculation
try:
    encoding = tiktoken.get_encoding("cl100k_base")
except:
    encoding = None


class DocumentProcessor:
    """Processes documents for semantic chunking and embedding"""
    
    def __init__(self, model_name: str = None, chunk_size: int = 512, chunk_overlap: int = 50):
        """
        Initialize document processor
        
        Args:
            model_name: Sentence transformer model name
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Token overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.model_name = model_name or os.getenv(
            "EMBEDDING_MODEL", 
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.embedding_model = None
        
    def _get_embedding_model(self):
        """Lazy load embedding model"""
        if self.embedding_model is None:
            self.embedding_model = SentenceTransformer(self.model_name)
        return self.embedding_model
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if encoding:
            return len(encoding.encode(text))
        # Fallback: approximate token count (1 token ≈ 4 characters)
        return len(text) // 4
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences (supports Turkish and English)"""
        # Pattern for sentence endings (Turkish and English)
        sentence_endings = r'[.!?]\s+'
        sentences = re.split(sentence_endings, text)
        # Filter out empty sentences
        return [s.strip() for s in sentences if s.strip()]
    
    def chunk_text_semantic(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Chunk text semantically preserving sentence boundaries
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of chunk dictionaries with text, metadata, and index
        """
        if not text or not text.strip():
            return []
        
        sentences = self.split_into_sentences(text)
        if not sentences:
            return []
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            # If single sentence exceeds chunk size, split it further
            if sentence_tokens > self.chunk_size:
                # Split long sentence by commas or other punctuation
                parts = re.split(r'[,;]\s+', sentence)
                for part in parts:
                    part_tokens = self.count_tokens(part)
                    if current_tokens + part_tokens > self.chunk_size and current_chunk:
                        # Save current chunk
                        chunk_text = ' '.join(current_chunk)
                        chunks.append({
                            'text': chunk_text,
                            'chunk_index': chunk_index,
                            'tokens': current_tokens,
                            'metadata': metadata or {}
                        })
                        chunk_index += 1
                        
                        # Start new chunk with overlap
                        overlap_sentences = current_chunk[-self._get_overlap_sentences():]
                        current_chunk = overlap_sentences + [part]
                        current_tokens = sum(self.count_tokens(s) for s in current_chunk)
                    else:
                        current_chunk.append(part)
                        current_tokens += part_tokens
            else:
                # Check if adding this sentence would exceed chunk size
                if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunk_text = ' '.join(current_chunk)
                    chunks.append({
                        'text': chunk_text,
                        'chunk_index': chunk_index,
                        'tokens': current_tokens,
                        'metadata': metadata or {}
                    })
                    chunk_index += 1
                    
                    # Start new chunk with overlap
                    overlap_sentences = current_chunk[-self._get_overlap_sentences():]
                    current_chunk = overlap_sentences + [sentence]
                    current_tokens = sum(self.count_tokens(s) for s in current_chunk)
                else:
                    current_chunk.append(sentence)
                    current_tokens += sentence_tokens
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'chunk_index': chunk_index,
                'tokens': current_tokens,
                'metadata': metadata or {}
            })
        
        return chunks
    
    def _get_overlap_sentences(self) -> int:
        """Calculate number of sentences for overlap"""
        # Approximate: assume average sentence is 20 tokens
        avg_sentence_tokens = 20
        overlap_sentences = max(1, self.chunk_overlap // avg_sentence_tokens)
        return overlap_sentences
    
    def extract_metadata(self, text: str, doc_type: str = None) -> Dict:
        """
        Extract metadata from document text
        
        Args:
            text: Document text
            doc_type: Type of document (itinerary, route, destination_info)
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            'type': doc_type or 'general',
            'language': self.detect_language(text),
            'word_count': len(text.split()),
            'char_count': len(text)
        }
        
        # Extract location mentions (common Turkish city names in GAP region)
        locations = self._extract_locations(text)
        if locations:
            metadata['locations'] = locations
        
        # Extract category/keywords
        categories = self._extract_categories(text)
        if categories:
            metadata['categories'] = categories
        
        return metadata
    
    def detect_language(self, text: str) -> str:
        """Detect if text is Turkish or English"""
        # Simple heuristic: check for Turkish-specific characters
        turkish_chars = set('çğıöşüÇĞIİÖŞÜ')
        text_chars = set(text)
        
        if turkish_chars.intersection(text_chars):
            return 'tr'
        
        # Check for common Turkish words
        turkish_words = ['ve', 'bir', 'ile', 'için', 'olan', 'bu', 'şu', 'o']
        words = text.lower().split()
        turkish_word_count = sum(1 for word in words if word in turkish_words)
        
        if turkish_word_count > len(words) * 0.1:
            return 'tr'
        
        return 'en'
    
    def _extract_locations(self, text: str) -> List[str]:
        """Extract location names from text"""
        # Common GAP region locations
        gap_locations = [
            'Şanlıurfa', 'Urfa', 'Gaziantep', 'Antep', 'Diyarbakır',
            'Mardin', 'Batman', 'Siirt', 'Şırnak', 'Adıyaman',
            'Göbeklitepe', 'Balıklıgöl', 'Nemrut', 'Harran', 'Hasankeyf',
            'Mardin Kalesi', 'Diyarbakır Surları', 'Zeugma'
        ]
        
        found_locations = []
        text_lower = text.lower()
        
        for location in gap_locations:
            if location.lower() in text_lower:
                found_locations.append(location)
        
        return list(set(found_locations))
    
    def _extract_categories(self, text: str) -> List[str]:
        """Extract category keywords from text"""
        categories = []
        text_lower = text.lower()
        
        category_keywords = {
            'tarih': ['tarih', 'tarihi', 'arkeoloji', 'arkeolojik', 'antik', 'eski'],
            'din': ['din', 'dini', 'kutsal', 'cami', 'kilise', 'manastır'],
            'doğa': ['doğa', 'doğal', 'dağ', 'nehir', 'göl', 'vadi', 'kanyon'],
            'kültür': ['kültür', 'kültürel', 'gelenek', 'festival', 'sanat'],
            'yemek': ['yemek', 'mutfak', 'lezzet', 'restoran', 'lokanta'],
            'konaklama': ['otel', 'hotel', 'konaklama', 'pansiyon', 'butik']
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                categories.append(category)
        
        return categories
    
    def process_document(self, text: str, title: str = None, doc_type: str = None, 
                        source: str = None) -> Dict:
        """
        Process a complete document: extract metadata and create chunks
        
        Args:
            text: Document text
            title: Document title
            doc_type: Type of document
            source: Document source
            
        Returns:
            Dictionary with processed document data
        """
        # Extract metadata
        metadata = self.extract_metadata(text, doc_type)
        metadata['title'] = title
        metadata['source'] = source
        
        # Create chunks
        chunks = self.chunk_text_semantic(text, metadata)
        
        return {
            'title': title,
            'text': text,
            'type': doc_type or 'general',
            'source': source,
            'metadata': metadata,
            'chunks': chunks,
            'chunk_count': len(chunks)
        }
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text"""
        model = self._get_embedding_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Generate embeddings for all chunks"""
        model = self._get_embedding_model()
        
        texts = [chunk['text'] for chunk in chunks]
        embeddings = model.encode(texts, convert_to_numpy=True)
        
        # Add embeddings to chunks
        for i, chunk in enumerate(chunks):
            chunk['embedding'] = embeddings[i].tolist()
        
        return chunks

