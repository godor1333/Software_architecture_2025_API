import time
import uuid
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SentimentLabel(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"

class MarketTrend(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

class NamedEntity(BaseModel):
    name: str
    ticker: str
    exchange: str = "MOEX"  # MOEX, SPBX, NASDAQ
    sector: str = "General" # Banking, Oil & Gas, IT, Retail
    mentions_count: int = 1

class NewsItem(BaseModel):
    news_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    source: str = "Interfax"
    url: Optional[str] = None
    published_at: float = Field(default_factory=time.time)

class NewsAnalysisResult(BaseModel):
    news_id: str
    title: str
    overall_sentiment: SentimentLabel
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    entities: List[NamedEntity] = []
    key_drivers: List[str] = []
    processing_time_ms: float = 0.0
    processed_at: float = Field(default_factory=time.time)

class CompanySentimentAggregate(BaseModel):
    ticker: str
    company_name: str
    total_news_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    sentiment_index: float = 0.0  # от -1.0 (крайний негатив) до +1.0 (крайний позитив)
    market_trend: MarketTrend = MarketTrend.NEUTRAL
    recent_news: List[NewsAnalysisResult] = []

class NewsBatchRequest(BaseModel):
    items: List[NewsItem]

class NewsBatchResponse(BaseModel):
    total_processed: int
    positive_count: int
    negative_count: int
    neutral_count: int
    results: List[NewsAnalysisResult]
