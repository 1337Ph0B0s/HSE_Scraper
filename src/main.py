from __future__ import annotations

import argparse

from src.modules.config import DEFAULT_MAX_DELAY, DEFAULT_MIN_DELAY, DEFAULT_USER_AGENT
from src.modules.pipeline import run


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="HSE Notices Scraper (list -> detail) with SQLite resume.")
    p.add_argument("--db", default="data/processed/hse_notices.sqlite", help="SQLite file for checkpoint/resume.")
    p.add_argument("--out", default="data/processed/hse_notices.csv", help="Output CSV file.")
    p.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="User-Agent with real contact email.")
    p.add_argument("--min-delay", type=float, default=DEFAULT_MIN_DELAY, help="Min seconds between requests.")
    p.add_argument("--max-delay", type=float, default=DEFAULT_MAX_DELAY, help="Max seconds between requests.")
    p.add_argument("--start-page", type=int, default=1, help="Start page number.")
    p.add_argument("--pages", type=int, default=5, help="If not --all, number of pages to scrape.")
    p.add_argument("--all", action="store_true", help="Scrape until the last page (use with care).")
    p.add_argument("--commit-every", type=int, default=25, help="Commit to SQLite every N records.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_delay < args.min_delay:
        raise ValueError("--max-delay must be >= --min-delay")

    run(
        db_path=args.db,
        out_csv=args.out,
        user_agent=args.user_agent,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        start_page=args.start_page,
        pages=args.pages,
        scrape_all=args.all,
        commit_every=args.commit_every,
    )


if __name__ == "__main__":
    main()