from datetime import datetime
from data.historical_data import historical_data
from analyzer.candle_rules import calculate_base_signal, adjust_confidence, generate_reasoning
from config.settings import settings


class ReplayAgent:
    """Runs candle-based analysis as if it was at a past timestamp."""

    def replay(self, pair: str, timestamp: datetime) -> dict:
        """Analyze pair using candle data at a given timestamp."""
        print(f"[Replay] Analyzing {pair} at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}...")

        # Get candle data at timestamp
        candle_data = historical_data.get_candle_signals(pair, timestamp)

        if "error" in candle_data:
            return {
                "pair": pair,
                "timestamp": timestamp.isoformat(),
                "error": candle_data["error"],
            }

        # Get actual outcome for validation
        outcome = historical_data.get_actual_outcome(pair, timestamp)

        # Calculate signal using candle rules
        base_signal = calculate_base_signal(candle_data)
        confidence = adjust_confidence(base_signal, candle_data)
        reasoning = generate_reasoning(base_signal, candle_data)

        result = {
            "pair": pair,
            "timestamp": timestamp.isoformat(),
            "signal": base_signal,
            "confidence": confidence,
            "reasoning": reasoning,
            "price_at_signal": candle_data.get("close"),
            "candle": {
                "direction": candle_data.get("candle_direction"),
                "size_pct": candle_data.get("candle_size_pct"),
                "macd_crossover": candle_data.get("macd_crossover"),
                "bb_position": candle_data.get("bb_position"),
                "volume_ratio": candle_data.get("volume_ratio"),
            },
        }

        # Add actual outcome for validation
        if outcome:
            result["actual"] = outcome
            result["correct"] = self._is_correct(
                base_signal,
                outcome["actual_direction"],
                outcome["change_pct"]
            )

        return result

    def _is_correct(self, signal: str, actual_direction: str, change_pct: float, threshold: float = 0.2) -> bool:
        """Determine if signal was correct."""
        if signal == "NEUTRAL":
            return abs(change_pct) < threshold
        elif signal == "BUY":
            return actual_direction == "up"
        return False


replay_agent = ReplayAgent()
