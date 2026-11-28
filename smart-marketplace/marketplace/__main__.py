"""CLI entry point: python -m marketplace --help."""

import argparse
import json
from pathlib import Path
import sys

from .catalogue import expand_catalogue, load_catalogue, save_catalogue
from .search import linear_search
from .session01 import PROJECT_ROOT, run_session
from .module01 import run_all, run_session as run_numbered_session


def main() -> int:
    parser = argparse.ArgumentParser(description="Smart Marketplace | Module 1")
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="Find in-stock products strictly below a price limit")
    search.add_argument("--catalog", type=Path, default=PROJECT_ROOT / "data" / "products_20.json")
    search.add_argument("--category", default="laptop", help="Exact, case-sensitive category")
    search.add_argument("--max-price", type=int, default=60_000, help="Exclusive limit in whole INR")
    session = commands.add_parser("session1", help="Run the complete L01_T01 experiment")
    session.add_argument("--output", type=Path, default=PROJECT_ROOT / "results" / "session01")
    for number in range(2, 7):
        item = commands.add_parser(f"session{number}", help=f"Run Session {number}")
        item.add_argument("--output", type=Path, default=PROJECT_ROOT / "results" / f"session{number:02d}")
    module = commands.add_parser("module1", help="Run all six Module 1 sessions")
    module.add_argument("--output", type=Path, default=PROJECT_ROOT / "results")
    generate = commands.add_parser("generate", help="Expand the fixed fixture deterministically")
    generate.add_argument("--size", type=int, default=1_000)
    generate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "search":
            products = load_catalogue(args.catalog)
            ids = linear_search(products, args.category, args.max_price)
            print(json.dumps({"count": len(ids), "ids": ids}, indent=2))
        elif args.command == "session1":
            run_session(args.output)
        elif args.command == "module1":
            run_all(args.output)
        elif args.command.startswith("session"):
            run_numbered_session(int(args.command[-1]), args.output)
        else:
            fixture = load_catalogue(PROJECT_ROOT / "data" / "products_20.json")
            products = expand_catalogue(fixture, args.size)
            save_catalogue(products, args.output)
            print(f"Saved {len(products)} products to {args.output}")
    except (OSError, ValueError, AssertionError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
