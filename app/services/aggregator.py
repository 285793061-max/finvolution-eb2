from __future__ import annotations

from collections import Counter, defaultdict
from typing import List

from app.schemas import (
    AnalyzeSummary,
    DimensionSentimentStats,
    SentimentDistribution,
    ItemSentiment,
)


def _calc_distribution(items: List[ItemSentiment]) -> SentimentDistribution:
    total = len(items)
    counter = Counter(i.sentiment_label for i in items)
    positive = counter.get("positive", 0)
    neutral = counter.get("neutral", 0)
    negative = counter.get("negative", 0)

    def ratio(x: int) -> float:
        return float(x) / total if total > 0 else 0.0

    return SentimentDistribution(
        total=total,
        positive=positive,
        neutral=neutral,
        negative=negative,
        positive_ratio=ratio(positive),
        neutral_ratio=ratio(neutral),
        negative_ratio=ratio(negative),
    )


def _calc_by_dimension(items: List[ItemSentiment]) -> list[DimensionSentimentStats]:
    buckets: dict[str, list[ItemSentiment]] = defaultdict(list)
    for item in items:
        if not item.dimensions:
            continue
        for dim in item.dimensions:
            buckets[dim].append(item)

    result: list[DimensionSentimentStats] = []
    for dim, dim_items in buckets.items():
        dist = _calc_distribution(dim_items)
        result.append(
            DimensionSentimentStats(
                dimension=dim,
                total=dist.total,
                positive=dist.positive,
                neutral=dist.neutral,
                negative=dist.negative,
                positive_ratio=dist.positive_ratio,
                neutral_ratio=dist.neutral_ratio,
                negative_ratio=dist.negative_ratio,
            )
        )

    return result


def _calc_reputation_score(dist: SentimentDistribution) -> float:
    if dist.total == 0:
        return 50.0

    score = (dist.positive_ratio - dist.negative_ratio + 1) * 50
    return max(0.0, min(100.0, score))


def aggregate(items: List[ItemSentiment]) -> AnalyzeSummary:
    overall = _calc_distribution(items)
    by_dimension = _calc_by_dimension(items)
    reputation_score = _calc_reputation_score(overall)

    return AnalyzeSummary(
        overall=overall,
        by_dimension=by_dimension,
        reputation_score=reputation_score,
    )

