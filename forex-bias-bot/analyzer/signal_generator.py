from collector.forex_sentiment import forex_sentiment
from data.forex_data import forex_data
from analyzer.groq_client import groq_client


SYSTEM_PROMPT = """You are a professional forex trading analyst. Your task is to analyze market data and provide a 1-hour directional bias.

OUTPUT FORMAT (respond with ONLY this format):
SIGNAL: [BUY/SELL/NEUTRAL]
CONFIDELE: [0-100]%
REASONING: [brief explanation in 1 sentence]"""


class SignalGenerator:
    def __init__(self):
        self.sentiment = forex_sentiment
        self.market = forex_data
        self.llm = groq_client

    def generate(self, pair: str) -> dict:
        sentiment_data = self.sentiment.analyze(pair)
        technical_data = self.market.get_technicals(pair)

        prompt = self._build_prompt(pair, sentiment_data, technical_data)

        try:
            response = self.llm.generate(prompt, SYSTEM_PROMPT)
            signal_data = self.llm.parse_signal(response)
        except Exception as e:
            print(f"LLM error for {pair}: {e}")
            signal_data = {"signal": "NEUTRAL", "confidence": 50, "reasoning": "Error generating signal"}

        return {
            "pair": pair,
            "signal": signal_data["signal"],
            "confidence": signal_data["confidence"],
            "reasoning": signal_data["reasoning"],
            "sentiment_score": sentiment_data["sentiment_score"],
            "technical": technical_data,
            "news_headlines": sentiment_data["headlines"],
            "timestamp": None,
        }

    def _build_prompt(self, pair: str, sentiment: dict, technical: dict) -> str:
        headlines = "\n".join([f"- {h}" for h in sentiment.get("headlines", [])])

        technical_str = ""
        if technical:
            technical_str = f"""Technical Indicators:
- RSI (14): {technical.get('rsi', 'N/A')}
- MACD: {technical.get('macd', 'N/A')}
- MACD Signal: {technical.get('macd_signal', 'N/A')}
- MACD Histogram: {technical.get('macd_histogram', 'N/A')}
- Bollinger Upper: {technical.get('bb_upper', 'N/A')}
- Bollinger Lower: {technical.get('bb_lower', 'N/A')}
- BB Position: {technical.get('bb_position', 'N/A')}%
- Current Price: {technical.get('current_price', 'N/A')}
- 4h Price Change: {technical.get('price_change_4h_pct', 'N/A')}%"""

        prompt = f"""Analyze {pair} and provide a 1-hour trading bias.

News Sentiment (score {sentiment.get('sentiment_score', 'N/A')}/100):
{headlines if headlines else 'No recent news available'}

{technical_str}

Consider: news sentiment, technical indicators (RSI overbought/oversold, MACD crossover, Bollinger position), and price action.

Remember: Output ONLY your signal in the specified format."""

        return prompt


signal_generator = SignalGenerator()
