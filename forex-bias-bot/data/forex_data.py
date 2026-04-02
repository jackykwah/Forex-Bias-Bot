import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import ta
from config.settings import settings


class ForexData:
    def __init__(self):
        self.cache = {}

    def get_ohlcv(self, pair: str, period: str = "1h", interval: str = "1h") -> Optional[pd.DataFrame]:
        cache_key = f"{pair}_{period}_{interval}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if datetime.now() - cached_time < timedelta(minutes=settings.FOREX_CACHE_MINUTES):
                return cached_data

        ticker_symbol = self._pair_to_ticker(pair)
        try:
            ticker = yf.Ticker(ticker_symbol)
            data = ticker.history(period=period, interval=interval)
            if data.empty:
                return None

            self.cache[cache_key] = (datetime.now(), data)
            return data
        except Exception as e:
            print(f"yfinance error for {pair}: {e}")
            return None

    def get_technicals(self, pair: str) -> dict:
        df = self.get_ohlcv(pair)
        if df is None or df.empty:
            return {}

        close = df["Close"].dropna()
        if len(close) < 26:
            return {}

        close = close.squeeze() if hasattr(close, "squeeze") else close

        rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
        macd = ta.trend.MACD(close)
        bb = ta.volatility.BollingerBands(close, window=20)

        latest = close.iloc[-1]
        rsi_val = rsi.iloc[-1] if not rsi.empty else 50
        macd_val = macd.macd().iloc[-1] if not macd.macd().empty else 0
        macd_signal = macd.macd_signal().iloc[-1] if not macd.macd_signal().empty else 0
        bb_high = bb.bollinger_hband().iloc[-1] if not bb.bollinger_hband().empty else latest * 1.02
        bb_low = bb.bollinger_lband().iloc[-1] if not bb.bollinger_lband().empty else latest * 0.98

        price_change_pct = ((close.iloc[-1] - close.iloc[-4]) / close.iloc[-4] * 100) if len(close) >= 4 else 0

        return {
            "rsi": round(rsi_val, 2),
            "macd": round(macd_val, 5),
            "macd_signal": round(macd_signal, 5),
            "macd_histogram": round(macd_val - macd_signal, 5),
            "bb_upper": round(bb_high, 4),
            "bb_lower": round(bb_low, 4),
            "bb_position": round((latest - bb_low) / (bb_high - bb_low) * 100, 2) if bb_high != bb_low else 50,
            "current_price": round(latest, 4),
            "price_change_4h_pct": round(price_change_pct, 2),
            "candle_count": len(close),
        }

    def _pair_to_ticker(self, pair: str) -> str:
        return f"{pair.replace('/', '')}=X"


forex_data = ForexData()
