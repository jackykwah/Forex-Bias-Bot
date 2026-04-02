from typing import Optional
from collector.news_fetcher import news_fetcher


class ForexSentiment:
    def __init__(self):
        self.positive_keywords = [
            "rise", "rally", "surge", "gain", "bullish", "higher", "increase",
            "strong", "growth", "optimism", "boom", "profit", "positive", "up"
        ]
        self.negative_keywords = [
            "fall", "drop", "decline", "bearish", "lower", "decrease", "weak",
            "loss", "pessimism", "recession", "negative", "down", "crash"
        ]

    def analyze(self, pair: str) -> dict:
        news = news_fetcher.fetch_forex_news(pair, hours=4)

        if not news:
            return {
                "headlines": [],
                "sentiment_score": 50,
                "sentiment_label": "neutral",
                "article_count": 0,
            }

        headlines = [f"{n['title']} - {n['source']}" for n in news[:5]]
        score = self._calculate_score(news)

        return {
            "headlines": headlines,
            "sentiment_score": score,
            "sentiment_label": "positive" if score > 55 else "negative" if score < 45 else "neutral",
            "article_count": len(news),
        }

    def _calculate_score(self, news: list[dict]) -> int:
        if not news:
            return 50

        total_score = 0
        for article in news:
            text = f"{article.get('title', '')} {article.get('description', '')}".lower()
            score = 50

            pos_count = sum(1 for word in self.positive_keywords if word in text)
            neg_count = sum(1 for word in self.negative_keywords if word in text)

            if pos_count > neg_count:
                score = min(80, 50 + (pos_count - neg_count) * 10)
            elif neg_count > pos_count:
                score = max(20, 50 - (neg_count - pos_count) * 10)

            total_score += score

        return round(total_score / len(news))


forex_sentiment = ForexSentiment()
