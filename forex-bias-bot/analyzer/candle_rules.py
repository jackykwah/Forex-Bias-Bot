"""
Candle-based signal calculation module.
Uses MACD crossovers, Bollinger position, and price momentum.
No news required.
"""


def calculate_base_signal(candle_data: dict) -> str:
    """Calculate signal from candle data.

    Rules based on multiple confirmations:
    - MACD bullish crossover + price at lower BB = BUY
    - Strong momentum + BB position = directional
    - No confirmation = NEUTRAL
    - SELL signals removed - historical accuracy was 0%
    """
    if "error" in candle_data:
        return "NEUTRAL"

    macd_cross = candle_data.get("macd_crossover", "none")
    bb_position = candle_data.get("bb_position", 50)
    recent_momentum = candle_data.get("recent_momentum", "neutral")
    candle_direction = candle_data.get("candle_direction", "doji")

    # Strong BUY: MACD bullish crossover + price near lower BB
    if macd_cross == "bullish" and bb_position < 35:
        return "BUY"

    # Momentum-based BUY
    if recent_momentum == "up" and bb_position < 40:
        return "BUY"

    # Candle body strength - BUY only
    candle_dir = candle_data.get("candle_direction", "doji")
    candle_size = candle_data.get("candle_size_pct", 0)

    if candle_dir == "bullish" and candle_size > 0.1 and bb_position < 45:
        return "BUY"

    # Default to NEUTRAL
    return "NEUTRAL"


def adjust_confidence(base_signal: str, candle_data: dict) -> int:
    """Adjust confidence based on indicator alignment."""
    if "error" in candle_data:
        return 50

    bb_position = candle_data.get("bb_position", 50)
    volume_ratio = candle_data.get("volume_ratio", 1)
    candle_size = candle_data.get("candle_size_pct", 0)
    macd_cross = candle_data.get("macd_crossover", "none")

    base_conf = 50

    if base_signal == "BUY":
        base_conf = 60
        if macd_cross == "bullish":
            base_conf += 15
        if bb_position < 25:
            base_conf += 10
        elif bb_position < 35:
            base_conf += 5
        if candle_size > 0.15:
            base_conf += 5
        if volume_ratio > 1.5:
            base_conf += 5

    return min(95, max(30, base_conf))


def generate_reasoning(base_signal: str, candle_data: dict) -> str:
    """Generate brief reasoning text."""
    if "error" in candle_data:
        return "Insufficient data"

    reasons = []
    macd_cross = candle_data.get("macd_crossover", "none")
    bb_position = candle_data.get("bb_position", 50)
    recent_momentum = candle_data.get("recent_momentum", "neutral")

    if base_signal == "BUY":
        reasons.append("Bullish signal")
        if macd_cross == "bullish":
            reasons.append("MACD crossover bullish")
        if bb_position < 35:
            reasons.append(f"Price at lower BB ({bb_position:.0f})")
        if recent_momentum == "up":
            reasons.append("Recent momentum up")
    else:
        reasons.append("No clear signal - neutral")
        if bb_position < 30:
            reasons.append(f"Lower BB region ({bb_position:.0f})")
        elif bb_position > 70:
            reasons.append(f"Upper BB region ({bb_position:.0f})")

    return "; ".join(reasons)
