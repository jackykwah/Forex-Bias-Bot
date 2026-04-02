from analyzer.groq_client import groq_client
from analyzer.signal_rules import calculate_base_signal, adjust_confidence, generate_reasoning
from analyzer.tools import get_price, get_technicals, get_news
from config.settings import settings


class ForexAgent:
    """Rule-based forex signal agent - news drives direction, techs confirm."""

    def __init__(self):
        self.groq = groq_client

    def analyze(self, pair: str) -> dict:
        """Run rule-based analysis on a forex pair."""
        print(f"\n[Agent] Analyzing {pair} with rule-based signals...")

        # Gather data using tools
        print(f"[Agent] Fetching news for {pair}...")
        news_data = get_news(pair)
        news_sentiment = news_data.get("sentiment_score", 50)

        print(f"[Agent] Fetching technicals for {pair}...")
        tech_data = get_technicals(pair)
        macd_histogram = tech_data.get("macd_histogram", 0)
        bb_position = tech_data.get("bb_position", 50)

        print(f"[Agent] Fetching price for {pair}...")
        price_data = get_price(pair)
        current_price = price_data.get("price")

        # Calculate signal using rules
        base_signal = calculate_base_signal(news_sentiment, macd_histogram, bb_position)
        confidence = adjust_confidence(base_signal, news_sentiment, macd_histogram, bb_position)
        reasoning = generate_reasoning(base_signal, news_sentiment, macd_histogram, bb_position)

        result = {
            "pair": pair,
            "signal": base_signal,
            "confidence": confidence,
            "reasoning": reasoning,
            "current_price": current_price,
            "news_sentiment": news_sentiment,
            "technicals": {
                "macd_histogram": macd_histogram,
                "bb_position": bb_position,
            },
        }

        print(f"[Agent] Signal: {base_signal} ({confidence}%)")
        print(f"[Agent] Reasoning: {reasoning}")

        return result


forex_agent = ForexAgent()
