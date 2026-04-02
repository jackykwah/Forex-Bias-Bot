import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from scheduler.signal_logger import signal_logger


class Backtester:
    def __init__(self):
        self.neutral_threshold = 0.002  # 0.2%

    def get_price_at_time(self, pair: str, target_time: datetime) -> Optional[float]:
        """Fetch the price closest to the target time using period-based history."""
        ticker_symbol = self._pair_to_ticker(pair)
        try:
            ticker = yf.Ticker(ticker_symbol)
            # Use period instead of start/end - period='1d' gives us ~22 hours of 1h candles
            data = ticker.history(period="1d", interval="1h")
            if data.empty:
                return None

            # Remove timezone for comparison
            if data.index.tz is not None:
                data = data.tz_localize(None)

            # Find the closest candle to target time
            target_naive = target_time.replace(tzinfo=None)
            closest_idx = data.index.get_indexer([target_naive], method="nearest")[0]
            if closest_idx >= 0 and closest_idx < len(data):
                return float(data["Close"].iloc[closest_idx])
            return None
        except Exception as e:
            print(f"Error fetching price for {pair} at {target_time}: {e}")
            return None

    def validate_signal(self, signal: dict) -> dict:
        """Validate a single signal against price 1 hour later."""
        signal_id = signal["id"]
        pair = signal["pair"]
        signal_time = datetime.fromisoformat(signal["timestamp"])
        current_price = signal["current_price"]

        # Skip weekend signals - markets closed, no meaningful movement
        if signal_time.weekday() >= 5:
            return {"signal_id": signal_id, "outcome": "SKIPPED", "reason": "Weekend - market closed"}

        if not current_price:
            return {"signal_id": signal_id, "outcome": "PENDING", "reason": "No price data"}

        # Get price 1 hour later
        target_time = signal_time + timedelta(hours=1)
        price_1h_later = self.get_price_at_time(pair, target_time)

        if price_1h_later is None:
            return {"signal_id": signal_id, "outcome": "PENDING", "reason": "Could not fetch price"}

        price_change_pct = ((price_1h_later - current_price) / current_price) * 100

        # Determine outcome based on signal type
        signal_type = signal["signal"]
        if signal_type == "BUY":
            outcome = "CORRECT" if price_1h_later > current_price else "INCORRECT"
        elif signal_type == "SELL":
            outcome = "CORRECT" if price_1h_later < current_price else "INCORRECT"
        else:  # NEUTRAL
            outcome = "CORRECT" if abs(price_change_pct) < self.neutral_threshold * 100 else "INCORRECT"

        return {
            "signal_id": signal_id,
            "price_at_signal": current_price,
            "price_1h_later": price_1h_later,
            "price_change_pct": round(price_change_pct, 4),
            "outcome": outcome,
        }

    def backtest_pair(self, pair: str) -> dict:
        """Backtest all signals for a specific pair."""
        signals = signal_logger.get_unvalidated(pair)
        results = []
        for signal in signals:
            validation = self.validate_signal(signal)
            validation["pair"] = pair
            validation["signal_type"] = signal["signal"]
            validation["confidence"] = signal["confidence"]
            signal_logger.log_validation(validation)
            results.append(validation)

        return self._summarize(results, pair)

    def backtest_all(self) -> dict:
        """Backtest all unvalidated signals across all pairs."""
        all_results = {}
        for pair in ["USD/JPY", "GBP/JPY", "GBP/USD"]:
            summary = self.backtest_pair(pair)
            all_results[pair] = summary
        return all_results

    def _summarize(self, results: list, pair: str) -> dict:
        if not results:
            return {"pair": pair, "total": 0, "message": "No signals to validate"}

        total = len(results)
        correct = sum(1 for r in results if r["outcome"] == "CORRECT")
        pending = sum(1 for r in results if r["outcome"] == "PENDING")
        incorrect = total - correct - pending

        buy_signals = [r for r in results if r.get("signal_type") == "BUY"]
        sell_signals = [r for r in results if r.get("signal_type") == "SELL"]
        neutral_signals = [r for r in results if r.get("signal_type") == "NEUTRAL"]

        def calc_rate(sigs):
            if not sigs:
                return 0, 0
            correct_count = sum(1 for s in sigs if s["outcome"] == "CORRECT")
            return correct_count, len(sigs)

        buy_correct, buy_total = calc_rate(buy_signals)
        sell_correct, sell_total = calc_rate(sell_signals)
        neutral_correct, neutral_total = calc_rate(neutral_signals)

        return {
            "pair": pair,
            "total": total,
            "correct": correct,
            "incorrect": incorrect,
            "pending": pending,
            "accuracy": round(correct / (total - pending) * 100, 1) if (total - pending) > 0 else 0,
            "buy": {"correct": buy_correct, "total": buy_total},
            "sell": {"correct": sell_correct, "total": sell_total},
            "neutral": {"correct": neutral_correct, "total": neutral_total},
        }

    def _pair_to_ticker(self, pair: str) -> str:
        return f"{pair.replace('/', '')}=X"


backtester = Backtester()
