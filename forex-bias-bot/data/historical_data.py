import yfinance as yf
import ta
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


class HistoricalData:
    def get_historical_price(self, pair: str, target_time: datetime) -> Optional[float]:
        """Get the closing price closest to the target time using period-based fetch."""
        ticker_symbol = self._pair_to_ticker(pair)
        try:
            ticker = yf.Ticker(ticker_symbol)
            # Fetch 5 days to ensure we have enough historical data
            data = ticker.history(period="5d", interval="1h")
            if data.empty:
                return None

            # Remove timezone for comparison
            if data.index.tz is not None:
                data = data.tz_localize(None)

            # Filter to data before or at target time
            target_naive = target_time.replace(tzinfo=None)
            data = data[data.index <= target_naive]

            if data.empty:
                return None

            # Find closest to target
            closest_idx = data.index.get_indexer([target_naive], method="nearest")[0]
            if closest_idx >= 0 and closest_idx < len(data):
                return float(data["Close"].iloc[closest_idx])
            return None
        except Exception as e:
            print(f"Error fetching historical price for {pair} at {target_time}: {e}")
            return None

    def get_historical_technicals(self, pair: str, target_time: datetime) -> dict:
        """Get technical indicators calculated from data available at target_time."""
        ticker_symbol = self._pair_to_ticker(pair)
        try:
            ticker = yf.Ticker(ticker_symbol)
            # Fetch 5 days of hourly data
            data = ticker.history(period="5d", interval="1h")

            if data.empty or len(data) < 26:
                return {"error": "Insufficient historical data for technicals"}

            # Remove timezone
            if data.index.tz is not None:
                data = data.tz_localize(None)

            # Filter to only data BEFORE or AT target_time
            target_naive = target_time.replace(tzinfo=None)
            data = data[data.index <= target_naive]

            if len(data) < 26:
                return {"error": "Insufficient data before target time"}

            close = data["Close"].squeeze()

            # Calculate indicators
            rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
            macd = ta.trend.MACD(close)
            bb = ta.volatility.BollingerBands(close, window=20)

            latest = close.iloc[-1]
            rsi_val = rsi.iloc[-1]
            macd_val = macd.macd().iloc[-1]
            macd_signal = macd.macd_signal().iloc[-1]
            bb_high = bb.bollinger_hband().iloc[-1]
            bb_low = bb.bollinger_lband().iloc[-1]

            # Get price at target time
            price_at_time = float(data["Close"].iloc[-1])

            return {
                "pair": pair,
                "timestamp": target_time.isoformat(),
                "price": round(price_at_time, 5),
                "rsi": round(rsi_val, 2),
                "macd": round(macd_val, 5),
                "macd_signal": round(macd_signal, 5),
                "macd_histogram": round(macd_val - macd_signal, 5),
                "bb_upper": round(bb_high, 4),
                "bb_lower": round(bb_low, 4),
                "bb_position": round((latest - bb_low) / (bb_high - bb_low) * 100, 2),
            }
        except Exception as e:
            print(f"Error fetching historical technicals for {pair} at {target_time}: {e}")
            return {"error": str(e)}

    def get_candle_signals(self, pair: str, target_time: datetime, lookback: int = 5) -> dict:
        """Analyze candle patterns and momentum at a specific time."""
        ticker_symbol = self._pair_to_ticker(pair)
        try:
            ticker = yf.Ticker(ticker_symbol)
            data = ticker.history(period="5d", interval="1h")

            if data.empty:
                return {"error": "No data"}

            # Remove timezone
            if data.index.tz is not None:
                data = data.tz_localize(None)

            # Filter to data up to target time
            target_naive = target_time.replace(tzinfo=None)
            data = data[data.index <= target_naive]

            if len(data) < lookback + 2:
                return {"error": "Insufficient data"}

            # Get last few candles
            recent = data.iloc[-lookback-1:-1]  # Exclude current candle
            current = data.iloc[-1]

            close = data["Close"].iloc[-1]
            open_price = current["Open"]
            high = current["High"]
            low = current["Low"]

            # Candle momentum: current candle direction
            candle_body = close - open_price
            candle_size_pct = abs(candle_body / open_price) * 100 if open_price != 0 else 0

            # MACD from previous candles for crossover detection
            macd = ta.trend.MACD(data["Close"].iloc[:-1])  # Exclude current
            macd_vals = macd.macd()
            macd_signals = macd.macd_signal()

            if len(macd_vals) >= 2:
                prev_macd = macd_vals.iloc[-2]
                curr_macd = macd_vals.iloc[-1]
                prev_signal = macd_signals.iloc[-2]
                curr_signal = macd_signals.iloc[-1]

                # Detect crossover
                macd_crossover = "none"
                if prev_macd < prev_signal and curr_macd > curr_signal:
                    macd_crossover = "bullish"
                elif prev_macd > prev_signal and curr_macd < curr_signal:
                    macd_crossover = "bearish"
            else:
                macd_crossover = "none"

            # Recent momentum: compare last few closes
            if len(recent) >= 3:
                recent_momentum = "up" if close > recent["Close"].iloc[-3] else "down"
            else:
                recent_momentum = "neutral"

            # Bollinger position
            bb = ta.volatility.BollingerBands(data["Close"].iloc[:-1], window=20)
            bb_upper = bb.bollinger_hband().iloc[-1]
            bb_lower = bb.bollinger_lband().iloc[-1]
            bb_pos = (close - bb_lower) / (bb_upper - bb_lower) * 100 if bb_upper != bb_lower else 50

            # Average volume (simple check)
            avg_volume = data["Volume"].iloc[-5:].mean() if len(data) >= 5 else data["Volume"].mean()
            current_volume = data["Volume"].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

            return {
                "pair": pair,
                "timestamp": target_time.isoformat(),
                "close": round(close, 5),
                "candle_body": round(candle_body, 5),
                "candle_size_pct": round(candle_size_pct, 3),
                "candle_direction": "bullish" if candle_body > 0 else "bearish" if candle_body < 0 else "doji",
                "macd_crossover": macd_crossover,
                "recent_momentum": recent_momentum,
                "bb_position": round(bb_pos, 2),
                "volume_ratio": round(volume_ratio, 2),
                "high": round(high, 5),
                "low": round(low, 5),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_actual_outcome(self, pair: str, signal_time: datetime) -> Optional[dict]:
        """Get technical indicators calculated from data available at target_time."""
        ticker_symbol = self._pair_to_ticker(pair)
        try:
            ticker = yf.Ticker(ticker_symbol)
            # Fetch 5 days of hourly data
            data = ticker.history(period="5d", interval="1h")

            if data.empty or len(data) < 26:
                return {"error": "Insufficient historical data for technicals"}

            # Remove timezone
            if data.index.tz is not None:
                data = data.tz_localize(None)

            # Filter to only data BEFORE or AT target_time
            target_naive = target_time.replace(tzinfo=None)
            data = data[data.index <= target_naive]

            if len(data) < 26:
                return {"error": "Insufficient data before target time"}

            close = data["Close"].squeeze()

            # Calculate indicators
            rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
            macd = ta.trend.MACD(close)
            bb = ta.volatility.BollingerBands(close, window=20)

            latest = close.iloc[-1]
            rsi_val = rsi.iloc[-1]
            macd_val = macd.macd().iloc[-1]
            macd_signal = macd.macd_signal().iloc[-1]
            bb_high = bb.bollinger_hband().iloc[-1]
            bb_low = bb.bollinger_lband().iloc[-1]

            # Get price at target time
            price_at_time = float(data["Close"].iloc[-1])

            return {
                "pair": pair,
                "timestamp": target_time.isoformat(),
                "price": round(price_at_time, 5),
                "rsi": round(rsi_val, 2),
                "macd": round(macd_val, 5),
                "macd_signal": round(macd_signal, 5),
                "macd_histogram": round(macd_val - macd_signal, 5),
                "bb_upper": round(bb_high, 4),
                "bb_lower": round(bb_low, 4),
                "bb_position": round((latest - bb_low) / (bb_high - bb_low) * 100, 2),
            }
        except Exception as e:
            print(f"Error fetching historical technicals for {pair} at {target_time}: {e}")
            return {"error": str(e)}

    def get_actual_outcome(self, pair: str, signal_time: datetime) -> Optional[dict]:
        """Get the actual price change 1 hour after signal_time (for validation)."""
        price_at_signal = self.get_historical_price(pair, signal_time)
        price_1h_later = self.get_historical_price(pair, signal_time + timedelta(hours=1))

        if price_at_signal is None or price_1h_later is None:
            return None

        change_pct = ((price_1h_later - price_at_signal) / price_at_signal) * 100

        return {
            "price_at_signal": price_at_signal,
            "price_1h_later": price_1h_later,
            "change_pct": round(change_pct, 4),
            "actual_direction": "up" if price_1h_later > price_at_signal else "down" if price_1h_later < price_at_signal else "flat"
        }

    def _pair_to_ticker(self, pair: str) -> str:
        return f"{pair.replace('/', '')}=X"


historical_data = HistoricalData()
