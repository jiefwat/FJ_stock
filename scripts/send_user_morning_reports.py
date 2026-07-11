#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.send_morning_report import SendResult, send_morning_report
from stock_ts.account_settings import (
    DEFAULT_USER_DATA_DIR,
    iter_morning_email_preferences,
    mark_morning_email_sent,
    should_send_morning_email,
)
from stock_ts.config import get_settings

__all__ = ["SendResult", "UserMorningDispatchResult", "dispatch_due_user_reports"]


@dataclass(frozen=True)
class UserMorningDispatchResult:
    sent: int
    skipped: int
    failed: int
    markdown: str


def dispatch_due_user_reports(
    *,
    user_data_dir: str | Path | None = None,
    now: datetime | None = None,
    daily_dir: str | Path = "reports/daily",
    html_dir: str | Path = "reports/html",
    announcement_dir: str | Path = "reports/announcements",
    site_url: str = "https://stock.jiewat-kaka-fj.com",
    style: str = "digest",
    dry_run: bool = False,
    skip_if_email_missing: bool = False,
) -> UserMorningDispatchResult:
    resolved_user_data_dir = Path(
        user_data_dir or os.getenv("STOCK_TS_USER_DATA_DIR") or DEFAULT_USER_DATA_DIR
    )
    now = now or datetime.now(timezone(timedelta(hours=8)))
    settings = get_settings()
    preferences_list = iter_morning_email_preferences(user_data_dir=resolved_user_data_dir)
    lines = ["# StockTS 账号晨报发送结果", ""]
    if skip_if_email_missing and not (
        getattr(settings, "email_sender", "").strip()
        and getattr(settings, "email_password", "").strip()
    ):
        lines.append("- 邮箱未配置：缺少 EMAIL_SENDER 或 EMAIL_PASSWORD，已跳过本次发送。")
        return UserMorningDispatchResult(
            sent=0,
            skipped=len(preferences_list),
            failed=0,
            markdown="\n".join(lines) + "\n",
        )

    sent = 0
    skipped = 0
    failed = 0
    today = now.date().isoformat()
    for preferences in preferences_list:
        if not should_send_morning_email(preferences, now=now):
            skipped += 1
            continue
        holdings_path = resolved_user_data_dir / str(preferences.user_id) / "holdings.csv"
        result = send_morning_report(
            daily_dir=daily_dir,
            html_dir=html_dir,
            announcement_dir=announcement_dir,
            holdings_path=holdings_path,
            site_url=site_url,
            channels=["email"],
            email_receivers=preferences.receivers,
            dry_run=dry_run,
            style=style,
        )
        if result.ok:
            sent += 1
            if not dry_run:
                mark_morning_email_sent(
                    preferences,
                    sent_date=today,
                    user_data_dir=resolved_user_data_dir,
                )
            receiver_count = len(preferences.receivers)
            lines.append(f"- OK user={preferences.user_id}: sent to {receiver_count} receiver(s)")
        else:
            failed += 1
            detail = _first_result_line(result.markdown)
            lines.append(f"- FAIL user={preferences.user_id}: {detail}")
    if sent == 0 and failed == 0:
        lines.append("- 本次没有到达发送时间的账号晨报。")
    return UserMorningDispatchResult(
        sent=sent,
        skipped=skipped,
        failed=failed,
        markdown="\n".join(lines) + "\n",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send due per-user StockTS morning emails.")
    parser.add_argument(
        "--user-data-dir",
        default=os.getenv("STOCK_TS_USER_DATA_DIR", DEFAULT_USER_DATA_DIR),
    )
    parser.add_argument("--daily-dir", default="reports/daily")
    parser.add_argument("--html-dir", default="reports/html")
    parser.add_argument("--announcement-dir", default="reports/announcements")
    parser.add_argument("--site-url", default="https://stock.jiewat-kaka-fj.com")
    parser.add_argument("--style", default="digest")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-if-email-missing", action="store_true")
    parser.add_argument("--now", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    now = _parse_now(args.now) if args.now else None
    result = dispatch_due_user_reports(
        user_data_dir=args.user_data_dir,
        now=now,
        daily_dir=args.daily_dir,
        html_dir=args.html_dir,
        announcement_dir=args.announcement_dir,
        site_url=args.site_url,
        style=args.style,
        dry_run=args.dry_run,
        skip_if_email_missing=args.skip_if_email_missing,
    )
    print(result.markdown, end="")
    return 0 if result.failed == 0 else 2


def _parse_now(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone(timedelta(hours=8)))
    return parsed


def _first_result_line(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            return stripped[2:]
    return "未返回发送明细"


if __name__ == "__main__":
    raise SystemExit(main())
