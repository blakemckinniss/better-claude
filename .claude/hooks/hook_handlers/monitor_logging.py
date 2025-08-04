#!/usr/bin/env python3
"""
Monitoring script for the hook logging system.
Provides real-time insights into logging performance and health.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hook_logger import logger
from logger_integration import hook_logger as integration


def print_header():
    """Print monitoring header."""
    print("\n" + "=" * 80)
    print("HOOK LOGGING SYSTEM MONITOR")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")


def check_log_directory():
    """Check log directory structure and sizes."""
    print("📁 LOG DIRECTORY STATUS:")
    print("-" * 40)

    log_base = Path("/home/devcontainers/better-claude/.claude/logs")
    if not log_base.exists():
        print("❌ Log directory does not exist!")
        return

    total_size = 0
    file_count = 0

    for path in log_base.rglob("*"):
        if path.is_file():
            file_count += 1
            total_size += path.stat().st_size

    print(f"✓ Base directory: {log_base}")
    print(f"✓ Total files: {file_count}")
    print(f"✓ Total size: {total_size / (1024*1024):.2f} MB")

    # Check subdirectories
    subdirs = ["hooks", "system", "errors"]
    for subdir in subdirs:
        subpath = log_base / subdir
        if subpath.exists():
            count = len(list(subpath.rglob("*.jsonl")))
            print(f"  └─ {subdir}/: {count} log files")
    print()


def check_performance_metrics():
    """Check current performance metrics."""
    print("📊 PERFORMANCE METRICS:")
    print("-" * 40)

    # Get logger metrics
    metrics = logger.get_metrics()
    print(f"Total logs written: {metrics.get('total_logs', 0)}")
    print(f"Abridged entries: {metrics.get('abridged_count', 0)}")
    print(f"Errors encountered: {metrics.get('errors_count', 0)}")
    print(f"Runtime: {metrics.get('runtime_seconds', 0):.2f} seconds")
    print(f"Logs per second: {metrics.get('logs_per_second', 0):.2f}")

    # Get integration performance summary
    perf_summary = integration.get_performance_summary()
    if perf_summary:
        print(f"\nMemory usage: {perf_summary.get('current_memory_mb', 0):.2f} MB")
        print(f"Active hooks: {perf_summary.get('active_hooks', 0)}")
    print()


def check_recent_logs(minutes=5):
    """Check recent log activity."""
    print(f"📝 RECENT LOG ACTIVITY (last {minutes} minutes):")
    print("-" * 40)

    log_base = Path("/home/devcontainers/better-claude/.claude/logs/hooks")
    if not log_base.exists():
        print("No hooks log directory found")
        return

    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    recent_files = []

    for log_file in log_base.rglob("*.jsonl"):
        if log_file.stat().st_mtime > cutoff_time.timestamp():
            recent_files.append(log_file)

    if not recent_files:
        print(f"No logs written in the last {minutes} minutes")
    else:
        print(f"Found {len(recent_files)} recently modified log files:")
        for f in sorted(recent_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            print(f"  • {f.relative_to(log_base)} - {mtime.strftime('%H:%M:%S')}")
    print()


def test_logging_functionality():
    """Test basic logging functionality."""
    print("🧪 TESTING LOGGING FUNCTIONALITY:")
    print("-" * 40)

    test_data = {
        "hook_event_name": "MonitorTest",
        "session_id": "monitor-test-" + str(int(time.time())),
        "test": True,
        "timestamp": datetime.now().isoformat()
    }

    # Test entry logging
    print("Testing log_hook_entry...")
    integration.log_hook_entry(test_data, "MonitorTest")

    # Simulate some work
    time.sleep(0.1)

    # Test exit logging
    print("Testing log_hook_exit...")
    integration.log_hook_exit(test_data, 0, result="success")

    # Check if logs were written
    metrics_after = logger.get_metrics()
    print(f"✓ Logs written: {metrics_after['total_logs']}")

    # Test error logging
    print("\nTesting error logging...")
    error_data = test_data.copy()
    error_data["error_test"] = True
    integration.log_error(error_data, Exception("Test error for monitoring"))
    print("✓ Error logging tested")

    # Clean up stale performance data
    cleaned = integration.cleanup_stale_performance_data(max_age_seconds=0)
    print(f"\n✓ Cleaned up {cleaned} stale performance entries")
    print()


def generate_summary_report():
    """Generate a summary report."""
    print("📋 SUMMARY REPORT:")
    print("-" * 40)

    # Get session logs for today
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = Path(f"/home/devcontainers/better-claude/.claude/logs/hooks")

    hook_counts = {}
    total_today = 0

    if log_path.exists():
        for event_dir in log_path.iterdir():
            if event_dir.is_dir():
                date_path = event_dir / today
                if date_path.exists():
                    count = len(list(date_path.rglob("*.jsonl")))
                    if count > 0:
                        hook_counts[event_dir.name] = count
                        total_today += count

    if hook_counts:
        print(f"Today's activity ({today}):")
        for hook, count in sorted(hook_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {hook}: {count} logs")
        print(f"\nTotal logs today: {total_today}")
    else:
        print("No logs found for today")

    print("\n" + "=" * 80)


def main():
    """Run the monitoring script."""
    print_header()

    try:
        check_log_directory()
        check_performance_metrics()
        check_recent_logs()
        test_logging_functionality()
        generate_summary_report()

        print("\n✅ Monitoring completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during monitoring: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()