from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
from analyzer.agent import forex_agent
from config.settings import settings


def run_analysis(pair: str):
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Analyzing {pair}...")
    try:
        result = forex_agent.analyze(pair)
        print(f"[{pair}] Final Signal: {result['signal']} | Confidence: {result.get('confidence', 'N/A')}%")
        print(f"[{pair}] Reasoning: {result.get('reasoning', 'N/A')}")
        return result
    except Exception as e:
        print(f"[{pair}] Error: {e}")
        return None


def hourly_job():
    print(f"\n{'='*50}")
    print(f"Hourly Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    for pair in settings.TRADING_PAIRS:
        run_analysis(pair)


def start_scheduler():
    scheduler = BlockingScheduler()
    scheduler.add_job(hourly_job, "cron", minute=0)
    print("Scheduler started. Running hourly at minute 0.")
    print("Press Ctrl+C to exit.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nScheduler stopped.")
