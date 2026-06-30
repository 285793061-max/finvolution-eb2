from fastapi import APIRouter, HTTPException

from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.collector import fetch_texts
from app.services.nlp import analyze_items
from app.services.aggregator import aggregate


router = APIRouter(prefix="", tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    raw_items = fetch_texts(keyword=request.keyword, limit=request.limit)
    if not raw_items:
        raise HTTPException(status_code=404, detail="未找到匹配该关键词的文本数据")

    analyzed_items = analyze_items(raw_items)
    summary = aggregate(analyzed_items)

    return AnalyzeResponse(items=analyzed_items, summary=summary)

