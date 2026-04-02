import requests
from datetime import datetime
from config.settings import settings


class DiscordBot:
    def __init__(self):
        self.webhook_url = settings.DISCORD_WEBHOOK_URL

    def send_signal(self, signal_data: dict):
        if not self.webhook_url or self.webhook_url == "your_discord_webhook_url_here":
            print(f"[DISCORD] Signal: {signal_data['pair']} - {signal_data['signal']} (conf: {signal_data['confidence']}%)")
            return

        pair = signal_data["pair"]
        signal = signal_data["signal"]
        confidence = signal_data["confidence"]
        reasoning = signal_data.get("reasoning", "No reasoning provided")
        sentiment = signal_data.get("sentiment_score", 50)
        tech = signal_data.get("technical", {})

        color = {
            "BUY": 0x00FF00,
            "SELL": 0xFF0000,
            "NEUTRAL": 0xFFAA00,
        }.get(signal, 0xFFAA00)

        rsi = tech.get("rsi", "N/A")
        macd = tech.get("macd", "N/A")
        price = tech.get("current_price", "N/A")

        embed = {
            "title": f"{pair} - {signal}",
            "description": reasoning,
            "color": color,
            "fields": [
                {"name": "Confidence", "value": f"{confidence}%", "inline": True},
                {"name": "Sentiment", "value": str(sentiment), "inline": True},
                {"name": "Price", "value": str(price), "inline": True},
                {"name": "RSI (14)", "value": str(rsi), "inline": True},
                {"name": "MACD", "value": str(macd), "inline": True},
            ],
            "timestamp": datetime.now().isoformat(),
            "footer": {"text": "Forex Bias Bot"},
        }

        payload = {"embeds": [embed]}

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Discord webhook error: {e}")


discord_bot = DiscordBot()
