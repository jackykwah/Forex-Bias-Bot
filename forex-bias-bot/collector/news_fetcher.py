import requests
from datetime import datetime, timedelta
from typing import Optional
from config.settings import settings


class NewsFetcher:
    def __init__(self):
        self.api_key = settings.NEWS_API_KEY
        self.base_url = "https://newsapi.org/v2"
        self.cache = {}

    def fetch_forex_news(self, pair: str, hours: int = 4) -> list[dict]:
        cache_key = f"{pair}_{hours}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if datetime.now() - cached_time < timedelta(minutes=settings.NEWS_CACHE_MINUTES):
                return cached_data

        query = self._pair_to_query(pair)
        url = f"{self.base_url}/everything"
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "apiKey": self.api_key,
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            articles = data.get("articles", [])
            news_items = []
            cutoff = datetime.now() - timedelta(hours=hours)

            for article in articles:
                published_at = article.get("publishedAt", "")
                if published_at:
                    try:
                        pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                        if pub_date.replace(tzinfo=None) >= cutoff:
                            news_items.append({
                                "title": article.get("title", ""),
                                "description": article.get("description", ""),
                                "source": article.get("source", {}).get("name", ""),
                                "published_at": published_at,
                                "url": article.get("url", ""),
                            })
                    except (ValueError, TypeError):
                        continue

            self.cache[cache_key] = (datetime.now(), news_items)
            return news_items
        except requests.exceptions.RequestException as e:
            print(f"NewsAPI error for {pair}: {e}")
            return self.cache.get(cache_key, ([], datetime.now() - timedelta(hours=1)))[1]

    def _pair_to_query(self, pair: str) -> str:
        currencies = {
            "USD": "dollar USD",
            "JPY": "yen JPY Japanese yen",
            "GBP": "pound GBP British pound",
            "EUR": "euro EUR",
            "AUD": "AUD Australian dollar",
            "CAD": "CAD Canadian dollar",
            "NZD": "NZD New Zealand dollar",
        }

        parts = pair.split("/")
        if len(parts) == 2:
            base, quote = parts
            return f"forex {currencies.get(base, base)} {currencies.get(quote, quote)}"
        return f"forex {pair}"


news_fetcher = NewsFetcher()
