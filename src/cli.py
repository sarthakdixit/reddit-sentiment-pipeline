from __future__ import annotations

import argparse
import sys

from src.composition import build_ingestion_service


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reddit-pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Fetch posts and write to bronze")
    ingest.add_argument("--subreddit", default="technology")
    ingest.add_argument("--limit", type=int, default=100)

    args = parser.parse_args(argv)

    if args.command == "ingest":
        return _run_ingest(args.subreddit, args.limit)

    return 1


def _run_ingest(subreddit: str, limit: int) -> int:
    service = build_ingestion_service()
    count = service.ingest(subreddit=subreddit, limit=limit)
    print(f"Ingested {count} posts from r/{subreddit} into bronze")
    return 0


if __name__ == "__main__":
    sys.exit(main())
