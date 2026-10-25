import time
import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class BookDocument(BaseModel):
    book_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    author: str
    subject: str = "Computer Science"
    total_pages: int = 1
    content: str
    file_url: Optional[str] = None
    created_at: float = Field(default_factory=time.time)

class DocumentChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    book_id: str
    book_title: str
    author: str
    chunk_index: int
    page_number: int = 1
    text: str
    embedding: Optional[List[float]] = None

class SourceCitation(BaseModel):
    book_title: str
    author: str
    page_number: int
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    chunk_text: str

class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 3
    subject_filter: Optional[str] = None
    strategy: str = "dense_vector"  # dense_vector | hybrid_keyword_vector

class RAGQueryResponse(BaseModel):
    query: str
    generated_answer: str
    sources: List[SourceCitation] = []
    used_chunks_count: int = 0
    search_strategy: str = "dense_vector"
    latency_ms: float = 0.0

class IndexingResponse(BaseModel):
    book_id: str
    title: str
    chunks_indexed: int
    processing_time_ms: float
    status: str = "SUCCESS"

class RAGSystemMetrics(BaseModel):
    total_books: int
    total_chunks: int
    total_queries: int
    avg_query_latency_ms: float
    avg_retrieval_score: float
    top_queried_subjects: List[str] = []
