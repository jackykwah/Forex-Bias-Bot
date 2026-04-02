import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
    ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

    TRADING_PAIRS = [
        pair.strip() for pair in os.getenv("TRADING_PAIRS", "USD/JPY,GBP/JPY,GBP/USD").split(",")
    ]

    GROQ_MODEL = "llama-3.3-70b-versatile"

    NEWS_CACHE_MINUTES = 30
    FOREX_CACHE_MINUTES = 15

    def validate(self) -> list[str]:
        errors = []
        if not self.GROQ_API_KEY:
            errors.append("GROQ_API_KEY is required")
        if not self.NEWS_API_KEY:
            errors.append("NEWS_API_KEY is required")
        if not self.DISCORD_WEBHOOK_URL:
            errors.append("DISCORD_WEBHOOK_URL is required")
        return errors


settings = Settings()
