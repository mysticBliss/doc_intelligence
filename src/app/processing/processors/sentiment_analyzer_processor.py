import time
import structlog
from typing import Any, Dict, Set

import structlog

from app.processing.decorators import instrument_step
from app.processing.processors.base import BaseProcessor, ProcessorResult
from app.processing.payloads import DocumentPayload


class SentimentAnalyzerProcessor(BaseProcessor):
    name = "sentiment_analyzer"

    def __init__(self, config: Dict[str, Any], logger: structlog.stdlib.BoundLogger):
        super().__init__(config, logger)
        self.positive_words: Set[str] = set(self.config.get("positive_words", {"good", "great", "excellent", "positive", "awesome"}))
        self.negative_words: Set[str] = set(self.config.get("negative_words", {"bad", "poor", "terrible", "negative", "awful"}))

    @instrument_step
    async def process(self, *, payload: DocumentPayload, **kwargs: Any) -> ProcessorResult:
        if not payload.text_content:
            return ProcessorResult(
                processor_name=self.name,
                status="failure",
                error="Text content is required for sentiment analysis.",
            )

        words = payload.text_content.lower().split()
        score = 0
        for word in words:
            if word in self.positive_words:
                score += 1
            elif word in self.negative_words:
                score -= 1

        if score > 0:
            sentiment = "positive"
        elif score < 0:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return ProcessorResult(
            processor_name=self.name,
            status="success",
            results={"sentiment": sentiment, "score": score},
        )