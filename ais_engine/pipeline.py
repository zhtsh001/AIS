#!/usr/bin/env python3
"""Unified AIS pipeline CLI.

Replaces the legacy ``fetch.py`` / ``generate.py`` / ``publish.py`` /
``push_daily.py`` / ``push_weekly.py`` entry points with a single subcommand
surface, while delegating the actual work to the existing modules. Cron
plists, scripts, and docs should reference ``pipeline.py`` going forward.

Usage:
    python pipeline.py fetch
    python pipeline.py generate
    python pipeline.py publish-daily   [--scheduled] [--dry-run]
    python pipeline.py publish-weekly  [--scheduled] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys


def _cmd_fetch(_args: argparse.Namespace) -> None:
    from fetch import hourly_raw_fetch
    hourly_raw_fetch()


def _cmd_generate(_args: argparse.Namespace) -> None:
    from generate import run_ais_generate
    run_ais_generate()


def _cmd_publish_daily(args: argparse.Namespace) -> None:
    from publishers.orchestrator import run_daily_publish
    run_daily_publish(scheduled=args.scheduled, dry_run=args.dry_run)


def _cmd_publish_weekly(args: argparse.Namespace) -> None:
    from publishers.orchestrator import run_weekly_publish
    run_weekly_publish(scheduled=args.scheduled, dry_run=args.dry_run)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ais-pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fetch", help="Run the source ingestor cycle.")
    sub.add_parser("generate", help="Score + generate alpha signals from raw data.")

    p_daily = sub.add_parser("publish-daily", help="Daily publish cycle (BJ 08:08).")
    p_daily.add_argument("--scheduled", action="store_true",
                         help="Only run inside the configured BJ window.")
    p_daily.add_argument("--dry-run", action="store_true",
                         help="Build and archive batches but skip outbound sends.")

    p_weekly = sub.add_parser("publish-weekly", help="Weekly digest (Fri BJ 20:08).")
    p_weekly.add_argument("--scheduled", action="store_true")
    p_weekly.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    handlers = {
        "fetch": _cmd_fetch,
        "generate": _cmd_generate,
        "publish-daily": _cmd_publish_daily,
        "publish-weekly": _cmd_publish_weekly,
    }
    handlers[args.cmd](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
