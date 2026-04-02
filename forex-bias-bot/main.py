import sys
import argparse
from datetime import datetime
from config.settings import settings
from analyzer.agent import forex_agent
from scheduler.discord_bot import discord_bot
from scheduler.signal_logger import signal_logger
from scheduler.hourly_job import start_scheduler, run_analysis
from validator.backtester import backtester
from validator.replay_backtester import replay_backtester


def test_connections():
    print("Testing API connections...")
    print(f"  Groq API: {'Configured' if settings.GROQ_API_KEY else 'MISSING'}")
    print(f"  NewsAPI: {'Configured' if settings.NEWS_API_KEY else 'MISSING'}")
    print(f"  Discord: {'Configured' if settings.DISCORD_WEBHOOK_URL else 'MISSING'}")
    print(f"  Trading pairs: {settings.TRADING_PAIRS}")

    errors = settings.validate()
    if errors:
        print("\nConfiguration errors:")
        for err in errors:
            print(f"  - {err}")
        return False

    print("\nAll APIs configured!")
    return True


def analyze_pair(pair: str):
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Analyzing {pair}...")
    result = forex_agent.analyze(pair)
    result["timestamp"] = datetime.now()

    signal_logger.log(result)
    discord_bot.send_signal(result)

    print(f"\n{'='*50}")
    print(f"RESULT: {pair}")
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result.get('confidence', 'N/A')}%")
    print(f"Reasoning: {result.get('reasoning', 'N/A')}")
    print(f"{'='*50}")

    return result


def run_backtest(pair: str = None):
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running backtest...")
    if pair:
        print(f"Backtesting {pair}...")
        result = backtester.backtest_pair(pair)
        _print_summary(result)
    else:
        print("Backtesting all pairs...")
        results = backtester.backtest_all()
        for pair_result in results.values():
            _print_summary(pair_result)
            print()


def _print_summary(summary: dict):
    print(f"\n{'='*50}")
    print(f"PAIR: {summary.get('pair', 'N/A')}")
    print(f"{'='*50}")
    print(f"Total signals: {summary.get('total', 0)}")
    if summary.get('pending', 0) > 0:
        print(f"Pending: {summary.get('pending', 0)}")
    print(f"Correct: {summary.get('correct', 0)}")
    print(f"Incorrect: {summary.get('incorrect', 0)}")
    if summary.get('total', 0) > 0 and summary.get('pending', 0) < summary.get('total', 0):
        print(f"Accuracy: {summary.get('accuracy', 0)}%")

    buy = summary.get('buy', {})
    sell = summary.get('sell', {})
    neutral = summary.get('neutral', {})
    if buy.get('total', 0) > 0:
        rate = round(buy['correct'] / buy['total'] * 100, 1) if buy['total'] > 0 else 0
        print(f"  BUY:  {buy['correct']}/{buy['total']} ({rate}%)")
    if sell.get('total', 0) > 0:
        rate = round(sell['correct'] / sell['total'] * 100, 1) if sell['total'] > 0 else 0
        print(f"  SELL: {sell['correct']}/{sell['total']} ({rate}%)")
    if neutral.get('total', 0) > 0:
        rate = round(neutral['correct'] / neutral['total'] * 100, 1) if neutral['total'] > 0 else 0
        print(f"  NEUTRAL: {neutral['correct']}/{neutral['total']} ({rate}%)")


def show_stats(pair: str = None):
    stats = signal_logger.get_stats(pair)
    if not stats:
        print("No validated signals yet. Run --backtest first.")
        return

    by_pair = {}
    for row in stats:
        p = row['pair']
        if p not in by_pair:
            by_pair[p] = {'correct': 0, 'incorrect': 0, 'total': 0}
        by_pair[p]['total'] += 1
        if row['outcome'] == 'CORRECT':
            by_pair[p]['correct'] += 1
        else:
            by_pair[p]['incorrect'] += 1

    print("\n=== SIGNAL ACCURACY STATS ===")
    for pair, data in by_pair.items():
        acc = round(data['correct'] / data['total'] * 100, 1) if data['total'] > 0 else 0
        print(f"{pair}: {data['correct']}/{data['total']} correct ({acc}%)")


def run_replay(pair: str, hours: int = 24):
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running replay backtest...")
    print(f"Testing {pair} over last {hours} hours...\n")
    result = replay_backtester.run_replay(pair.upper(), hours)
    _print_replay_summary(result)


def _print_replay_summary(summary: dict):
    print(f"\n{'='*50}")
    print(f"REPLAY BACKTEST: {summary.get('pair', 'N/A')} (Last {summary.get('hours_tested', 0)} hours)")
    print(f"{'='*50}")
    print(f"Total: {summary.get('total', 0)}")
    print(f"Correct: {summary.get('correct', 0)} ({summary.get('accuracy', 0)}%)")

    buy = summary.get('buy', {})
    sell = summary.get('sell', {})
    neutral = summary.get('neutral', {})

    if buy.get('total', 0) > 0:
        rate = round(buy['correct'] / buy['total'] * 100, 1) if buy['total'] > 0 else 0
        print(f"  BUY:  {buy['correct']}/{buy['total']} ({rate}%)")
    if sell.get('total', 0) > 0:
        rate = round(sell['correct'] / sell['total'] * 100, 1) if sell['total'] > 0 else 0
        print(f"  SELL: {sell['correct']}/{sell['total']} ({rate}%)")
    if neutral.get('total', 0) > 0:
        rate = round(neutral['correct'] / neutral['total'] * 100, 1) if neutral['total'] > 0 else 0
        print(f"  NEUTRAL: {neutral['correct']}/{neutral['total']} ({rate}%)")

    if summary.get('avg_confidence_correct'):
        print(f"\nAvg confidence when correct: {summary.get('avg_confidence_correct')}%")
        print(f"Avg confidence when wrong: {summary.get('avg_confidence_wrong')}%")


def main():
    parser = argparse.ArgumentParser(description="Forex Bias Signal Bot")
    parser.add_argument("--test", action="store_true", help="Test API connections")
    parser.add_argument("--analyze", type=str, help="Analyze a specific pair (e.g., USD/JPY)")
    parser.add_argument("--start", action="store_true", help="Start hourly scheduler")
    parser.add_argument("--backtest", nargs="?", const="all", type=str, help="Backtest signals. Use with pair name or leave empty for all")
    parser.add_argument("--stats", nargs="?", const="all", type=str, help="Show validation stats. Use with pair name or leave empty for all")
    parser.add_argument("--replay", nargs=2, metavar=("PAIR", "HOURS"), type=str, help="Replay backtest: PAIR HOURS (e.g., USD/JPY 24)")

    args = parser.parse_args()

    if args.test:
        test_connections()
    elif args.analyze:
        analyze_pair(args.analyze.upper())
    elif args.start:
        if not test_connections():
            print("\nPlease configure your .env file before starting.")
            sys.exit(1)
        start_scheduler()
    elif args.backtest is not None:
        pair = args.backtest if args.backtest != "all" else None
        run_backtest(pair.upper() if pair else None)
    elif args.stats is not None:
        pair = args.stats if args.stats != "all" else None
        show_stats(pair.upper() if pair else None)
    elif args.replay:
        pair, hours = args.replay
        run_replay(pair.upper(), int(hours))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
