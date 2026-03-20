import argparse
import os
import subprocess
import sys
import time


def parse_args():
    parser = argparse.ArgumentParser(description="Run Scrapy spiders in production-safe mode.")
    parser.add_argument(
        "--spiders",
        default=os.getenv("SPIDERS", ""),
        help="Comma-separated spider names. If omitted, all spiders will run.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop immediately when a spider fails.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=int(os.getenv("SPIDER_TIMEOUT_SECONDS", "0")),
        help="Per-spider timeout in seconds (0 disables timeout).",
    )
    return parser.parse_args()


def list_spiders():
    result = subprocess.run(
        [sys.executable, "-m", "scrapy", "list"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Unable to list spiders: {result.stderr.strip()}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def run_spider(spider_name, timeout_seconds):
    print(f"\n=== START spider: {spider_name} ===")
    start = time.time()
    cmd = [sys.executable, "-m", "scrapy", "crawl", spider_name]
    try:
        completed = subprocess.run(cmd, check=False, timeout=timeout_seconds if timeout_seconds > 0 else None)
        elapsed = int(time.time() - start)
        print(f"=== END spider: {spider_name} | exit={completed.returncode} | duration={elapsed}s ===")
        return completed.returncode
    except subprocess.TimeoutExpired:
        elapsed = int(time.time() - start)
        print(f"=== TIMEOUT spider: {spider_name} | duration={elapsed}s ===")
        return 124


def main():
    args = parse_args()
    available = list_spiders()

    if args.spiders.strip():
        requested = [s.strip() for s in args.spiders.split(",") if s.strip()]
        missing = [s for s in requested if s not in available]
        if missing:
            print(f"Unknown spider(s): {', '.join(missing)}")
            print(f"Available spiders: {', '.join(available)}")
            return 2
        spiders_to_run = requested
    else:
        spiders_to_run = available

    if not spiders_to_run:
        print("No spiders found to run.")
        return 0

    print(f"Running {len(spiders_to_run)} spider(s): {', '.join(spiders_to_run)}")
    failed = []

    for spider_name in spiders_to_run:
        code = run_spider(spider_name, args.timeout_seconds)
        if code != 0:
            failed.append((spider_name, code))
            if args.fail_fast:
                break

    if failed:
        print("\nFailed spiders:")
        for spider_name, code in failed:
            print(f"- {spider_name}: exit code {code}")
        return 1

    print("\nAll spiders completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
