#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from stock_ts.daily_artifacts import DailyArtifactConfig, run_daily_artifact_job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate StockTS daily markdown/html artifacts for Web and systemd timers."
    )
    parser.add_argument("--provider", default="tdx-snapshot")
    parser.add_argument("--snapshot")
    parser.add_argument("--holdings", default="data/portfolio/holdings.csv")
    parser.add_argument("--transactions")
    parser.add_argument("--news")
    parser.add_argument("--candidate-limit", type=int, default=20)
    parser.add_argument("--focus", help="Comma separated focus stock codes")
    parser.add_argument("--output-dir", default="reports/daily")
    parser.add_argument("--html-dir", default="reports/html")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.snapshot:
        os.environ["STOCK_TS_TDX_SNAPSHOT_PATH"] = args.snapshot
    focus_codes = tuple(item.strip() for item in (args.focus or "").split(",") if item.strip())
    result = run_daily_artifact_job(
        DailyArtifactConfig(
            provider_name=args.provider,
            holdings_path=Path(args.holdings),
            transactions_path=Path(args.transactions) if args.transactions else None,
            news_path=Path(args.news) if args.news else None,
            output_dir=Path(args.output_dir),
            html_dir=Path(args.html_dir),
            candidate_limit=args.candidate_limit,
            focus_codes=focus_codes,
        )
    )
    print(result.status_path)
    if not result.ok:
        print(result.error)
        return 2
    print(result.markdown_latest)
    print(result.html_latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
