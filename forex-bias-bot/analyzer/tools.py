import yfinance as yf
from collector.forex_sentiment import forex_sentiment
from scheduler.signal_logger import signal_logger
from scheduler.discord_bot import discord_bot
from config.settings import settings


def get_price(pair: str) -> dict:
    """Get current price and daily change for a forex pair."""
    ticker_symbol = _pair_to_ticker(pair)
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1d", interval="1h")
        if hist.empty:
            return {"error": f"No price data available for {pair}"}

        current_price = float(hist["Close"].iloc[-1])
        if len(hist) >= 24:
            daily_change = ((current_price - float(hist["Close"].iloc[-24])) / float(hist["Close"].iloc[-24])) * 100
        else:
            daily_change = 0.0

        return {
            "pair": pair,
            "price": round(current_price, 5),
            "daily_change_pct": round(daily_change, 3),
        }
    except Exception as e:
        return {"error": f"Failed to get price for {pair}: {str(e)}"}


def get_technicals(pair: str) -> dict:
    """Get RSI, MACD, Bollinger Bands for a forex pair."""
    ticker_symbol = _pair_to_ticker(pair)
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1d", interval="1h")
        if hist.empty or len(hist) < 26:
            return {"error": f"Insufficient data for technicals on {pair}"}

        import ta
        close = hist["Close"].squeeze()

        rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
        macd = ta.trend.MACD(close)
        bb = ta.volatility.BollingerBands(close, window=20)

        latest = close.iloc[-1]
        rsi_val = rsi.iloc[-1]
        macd_val = macd.macd().iloc[-1]
        macd_signal = macd.macd_signal().iloc[-1]
        bb_high = bb.bollinger_hband().iloc[-1]
        bb_low = bb.bollinger_lband().iloc[-1]

        return {
            "pair": pair,
            "rsi": round(rsi_val, 2),
            "macd": round(macd_val, 5),
            "macd_signal": round(macd_signal, 5),
            "macd_histogram": round(macd_val - macd_signal, 5),
            "bb_upper": round(bb_high, 4),
            "bb_lower": round(bb_low, 4),
            "bb_position": round((latest - bb_low) / (bb_high - bb_low) * 100, 2),
            "current_price": round(latest, 5),
        }
    except Exception as e:
        return {"error": f"Failed to get technicals for {pair}: {str(e)}"}


def get_news(pair: str) -> dict:
    """Get recent news headlines for a forex pair."""
    try:
        sentiment = forex_sentiment.analyze(pair)
        return {
            "pair": pair,
            "headlines": sentiment.get("headlines", []),
            "sentiment_score": sentiment.get("sentiment_score", 50),
            "sentiment_label": sentiment.get("sentiment_label", "neutral"),
            "article_count": sentiment.get("article_count", 0),
        }
    except Exception as e:
        return {"error": f"Failed to get news for {pair}: {str(e)}"}


def get_historical_stats(pair: str) -> dict:
    """Get historical signal accuracy for a forex pair."""
    try:
        stats = signal_logger.get_stats(pair)
        if not stats:
            return {
                "pair": pair,
                "total_signals": 0,
                "message": "No historical data yet",
            }

        buy_signals = [s for s in stats if s["signal"] == "BUY"]
        sell_signals = [s for s in stats if s["signal"] == "SELL"]
        neutral_signals = [s for s in stats if s["signal"] == "NEUTRAL"]

        def calc_accuracy(sig_list):
            if not sig_list:
                return None
            correct = sum(1 for s in sig_list if s["outcome"] == "CORRECT")
            return round(correct / len(sig_list) * 100, 1)

        return {
            "pair": pair,
            "total_signals": len(stats),
            "buy_accuracy": calc_accuracy(buy_signals),
            "buy_total": len(buy_signals),
            "sell_accuracy": calc_accuracy(sell_signals),
            "sell_total": len(sell_signals),
            "neutral_accuracy": calc_accuracy(neutral_signals),
            "neutral_total": len(neutral_signals),
        }
    except Exception as e:
        return {"error": f"Failed to get stats for {pair}: {str(e)}"}


def send_signal(pair: str, signal: str, confidence: int, reasoning: str) -> dict:
    """Send trading signal to Discord."""
    try:
        signal_data = {
            "pair": pair,
            "signal": signal,
            "confidence": confidence,
            "reasoning": reasoning,
        }
        discord_bot.send_signal(signal_data)
        signal_logger.log(signal_data)
        return {
            "success": True,
            "message": f"Signal sent for {pair}: {signal} ({confidence}% confidence)",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to send signal: {str(e)}"}


def _pair_to_ticker(pair: str) -> str:
    return f"{pair.replace('/', '')}=X"


# Tool definitions for Groq API
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_price",
            "description": "Get current forex pair price and daily change percentage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "enum": ["USD/JPY", "GBP/JPY", "GBP/USD"],
                        "description": "The forex pair to get price for"
                    }
                },
                "required": ["pair"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_technicals",
            "description": "Get technical indicators (RSI, MACD, Bollinger Bands) for a forex pair.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "enum": ["USD/JPY", "GBP/JPY", "GBP/USD"],
                        "description": "The forex pair to get technicals for"
                    }
                },
                "required": ["pair"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Get recent forex news headlines and sentiment for a pair.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "enum": ["USD/JPY", "GBP/JPY", "GBP/USD"],
                        "description": "The forex pair to get news for"
                    }
                },
                "required": ["pair"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_historical_stats",
            "description": "Get historical signal accuracy for a forex pair - how often BUY, SELL, NEUTRAL signals have been correct.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "enum": ["USD/JPY", "GBP/JPY", "GBP/USD"],
                        "description": "The forex pair to get historical stats for"
                    }
                },
                "required": ["pair"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_signal",
            "description": "Send the final trading signal to Discord and log it. Only call this with your FINAL decision.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "enum": ["USD/JPY", "GBP/JPY", "GBP/USD"],
                        "description": "The forex pair"
                    },
                    "signal": {
                        "type": "string",
                        "enum": ["BUY", "SELL", "NEUTRAL"],
                        "description": "The trading signal"
                    },
                    "confidence": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Confidence level 0-100"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation for the signal"
                    }
                },
                "required": ["pair", "signal", "confidence", "reasoning"]
            }
        }
    }
]


# Map tool names to functions
TOOL_FUNCTIONS = {
    "get_price": get_price,
    "get_technicals": get_technicals,
    "get_news": get_news,
    "get_historical_stats": get_historical_stats,
    "send_signal": send_signal,
}
