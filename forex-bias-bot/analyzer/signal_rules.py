"""
Rule-based signal calculation module.
News sentiment drives direction, technicals provide confirmation.
"""


def calculate_base_signal(news_sentiment: float, macd_histogram: float, bb_position: float) -> str:
    """Calculate base signal from news sentiment (primary) and technicals (confirmation).

    Rules:
    - News sentiment > 55 (bullish) + MACD positive OR BB lower = BUY
    - News sentiment > 52 = BUY (lean bullish even without confirmation)
    - Otherwise: NEUTRAL
    - SELL signals removed - historical accuracy was 0%
    """

    # BUY: Bullish news + technical confirmation
    if news_sentiment > 55:
        if macd_histogram > 0 or bb_position < 30:
            return "BUY"

    # Weak BUY: Bullish news but no technical confirmation
    if news_sentiment > 52:
        return "BUY"

    # Default: Neutral
    return "NEUTRAL"


def adjust_confidence(base_signal: str, news_sentiment: float,
                      macd_histogram: float, bb_position: float) -> int:
    """Adjust confidence based on indicator alignment.

    Args:
        base_signal: Signal from calculate_base_signal
        news_sentiment: News sentiment score (0-100)
        macd_histogram: MACD histogram value
        bb_position: Bollinger Band position (0-100)

    Returns:
        Confidence level (30-95)
    """
    # Base confidence from news strength
    if base_signal == "BUY":
        news_strength = news_sentiment - 50
        base_conf = 50 + (news_strength * 0.6)  # 50-80 based on news
    else:
        base_conf = 50

    # Technical confirmation bonus
    if base_signal == "BUY":
        if macd_histogram > 0:
            base_conf += 10
        if bb_position < 30:
            base_conf += 10
        if bb_position < 20:
            base_conf += 5

    # Extreme news bonus
    if news_sentiment > 70:
        base_conf += 5

    return min(95, max(30, round(base_conf)))


def generate_reasoning(base_signal: str, news_sentiment: float,
                      macd_histogram: float, bb_position: float) -> str:
    """Generate brief reasoning text for the signal."""
    reasons = []

    # News sentiment
    if news_sentiment > 55:
        reasons.append(f"Bullish news ({news_sentiment:.0f})")
    elif news_sentiment > 52:
        reasons.append(f"Lean bullish news ({news_sentiment:.0f})")
    else:
        reasons.append(f"Neutral news ({news_sentiment:.0f})")

    # MACD
    if macd_histogram > 0.01:
        reasons.append(f"MACD bullish ({macd_histogram:.5f})")
    elif macd_histogram < -0.01:
        reasons.append(f"MACD bearish ({macd_histogram:.5f})")

    # Bollinger
    if bb_position < 25:
        reasons.append("Price near lower BB")
    elif bb_position > 75:
        reasons.append("Price near upper BB")

    return "; ".join(reasons) if reasons else "Mixed signals"
