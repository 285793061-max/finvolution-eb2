from datetime import datetime
from typing import Literal, List, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    keyword: str = Field(..., min_length=1, description="公司名称或关键词")
    limit: int = Field(100, ge=1, le=500, description="最大返回条数")


class ItemSentiment(BaseModel):
    id: str
    text: str
    source_type: str
    created_at: Optional[datetime] = None
    sentiment_label: Literal["positive", "neutral", "negative"]
    sentiment_score: float
    dimensions: List[str]


class SentimentDistribution(BaseModel):
    total: int
    positive: int
    neutral: int
    negative: int
    positive_ratio: float
    neutral_ratio: float
    negative_ratio: float


class DimensionSentimentStats(BaseModel):
    dimension: str
    total: int
    positive: int
    neutral: int
    negative: int
    positive_ratio: float
    neutral_ratio: float
    negative_ratio: float


class AnalyzeSummary(BaseModel):
    overall: SentimentDistribution
    by_dimension: List[DimensionSentimentStats]
    reputation_score: Optional[float] = None


class AnalyzeResponse(BaseModel):
    items: List[ItemSentiment]
    summary: AnalyzeSummary

