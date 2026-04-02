from datetime import datetime, timedelta
from typing import Optional
from analyzer.replay_agent import replay_agent


class ReplayBacktester:
    def run_replay(self, pair: str, hours_ago: int = 24) -> dict:
        """Replay the last N hours for a pair and return results."""
        print(f"[ReplayBacktest] Running replay for {pair} over last {hours_ago} hours...")

        results = []
        weekday_count = 0
        weekend_skipped = 0

        for i in range(hours_ago):
            timestamp = datetime.now() - timedelta(hours=i + 1)
            is_weekend = timestamp.weekday() >= 5  # 5=Sat, 6=Sun

            result = replay_agent.replay(pair, timestamp)
            results.append(result)

            # Print progress
            if "error" not in result:
                signal = result.get("signal", "?")
                if is_weekend:
                    actual_dir = result.get("actual", {}).get("actual_direction", "?") if "actual" in result else "?"
                    print(f"  [{timestamp.strftime('%a %H:%M')}] {signal} | Actual: {actual_dir} | SKIP (weekend)")
                    weekend_skipped += 1
                else:
                    correct = "OK" if result.get("correct") else "NO"
                    actual_dir = result.get("actual", {}).get("actual_direction", "?") if "actual" in result else "?"
                    print(f"  [{timestamp.strftime('%a %H:%M')}] {signal} | Actual: {actual_dir} | {correct}")
                    weekday_count += 1
            else:
                print(f"  [{timestamp.strftime('%a %H:%M')}] Error: {result.get('error')}")

        print(f"\n[Info] Weekday hours: {weekday_count}, Weekend hours skipped: {weekend_skipped}")
        return self._summarize(results, pair, hours_ago)

    def _summarize(self, results: list, pair: str, hours: int) -> dict:
        """Generate summary statistics - weekday only for accuracy."""
        # Only count weekday results with actual outcomes for accuracy
        valid_results = [r for r in results if "error" not in r and "actual" in r]

        if not valid_results:
            return {"pair": pair, "hours_tested": hours, "error": "No valid results"}

        total = len(valid_results)
        correct = sum(1 for r in valid_results if r.get("correct"))

        buy_results = [r for r in valid_results if r.get("signal") == "BUY"]
        sell_results = [r for r in valid_results if r.get("signal") == "SELL"]
        neutral_results = [r for r in valid_results if r.get("signal") == "NEUTRAL"]

        def calc_stats(sig_list):
            if not sig_list:
                return 0, 0
            c = sum(1 for r in sig_list if r.get("correct"))
            return c, len(sig_list)

        buy_correct, buy_total = calc_stats(buy_results)
        sell_correct, sell_total = calc_stats(sell_results)
        neutral_correct, neutral_total = calc_stats(neutral_results)

        avg_confidence_correct = 0
        avg_confidence_wrong = 0
        correct_confs = [r["confidence"] for r in valid_results if r.get("correct")]
        wrong_confs = [r["confidence"] for r in valid_results if not r.get("correct")]
        if correct_confs:
            avg_confidence_correct = sum(correct_confs) / len(correct_confs)
        if wrong_confs:
            avg_confidence_wrong = sum(wrong_confs) / len(wrong_confs)

        return {
            "pair": pair,
            "hours_tested": hours,
            "total": total,
            "correct": correct,
            "accuracy": round(correct / total * 100, 1) if total > 0 else 0,
            "buy": {"correct": buy_correct, "total": buy_total},
            "sell": {"correct": sell_correct, "total": sell_total},
            "neutral": {"correct": neutral_correct, "total": neutral_total},
            "avg_confidence_correct": round(avg_confidence_correct, 1),
            "avg_confidence_wrong": round(avg_confidence_wrong, 1),
        }


replay_backtester = ReplayBacktester()
