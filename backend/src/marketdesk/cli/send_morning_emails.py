from __future__ import annotations

import argparse
import asyncio
import json
import re
import smtplib
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

from marketdesk.config import Settings
from marketdesk.models import MorningEmailBrief, UserAccount
from marketdesk.services import MarketService

SMTP_CONFIGS = {
    "qq.com": ("smtp.qq.com", 465, "ssl"),
    "foxmail.com": ("smtp.qq.com", 465, "ssl"),
    "163.com": ("smtp.163.com", 465, "ssl"),
    "126.com": ("smtp.126.com", 465, "ssl"),
    "gmail.com": ("smtp.gmail.com", 587, "starttls"),
    "outlook.com": ("smtp-mail.outlook.com", 587, "starttls"),
    "hotmail.com": ("smtp-mail.outlook.com", 587, "starttls"),
    "live.com": ("smtp-mail.outlook.com", 587, "starttls"),
}


@dataclass(frozen=True)
class EmailAttempt:
    user_id: int
    recipient: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class DispatchSummary:
    sent: int
    skipped: int
    failed: int
    attempts: list[EmailAttempt]

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def to_markdown(self) -> str:
        lines = ["# StockTS 晨报发送结果", ""]
        if not self.attempts:
            lines.append("- 本次没有需要发送的账号晨报。")
        for attempt in self.attempts:
            mark = "OK" if attempt.ok else "FAIL"
            lines.append(f"- {mark} user={attempt.user_id} to={attempt.recipient}: {attempt.detail}")
        lines.append(f"- 汇总：sent={self.sent} skipped={self.skipped} failed={self.failed}")
        return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send enabled users the StockTS morning email brief.")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser


async def dispatch_morning_emails(
    *,
    settings: Settings | None = None,
    service: MarketService | None = None,
    base_url: str | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> DispatchSummary:
    resolved_settings = settings or Settings()
    resolved_service = service or MarketService()
    today = datetime.now(UTC).date().isoformat()
    state_path = resolved_settings.data_dir / "morning-email-sent.json"
    sent_users = set() if force else set(_load_sent_state(state_path).get(today, []))
    attempts: list[EmailAttempt] = []
    skipped = 0
    sent = 0
    failed = 0
    configured = bool(resolved_settings.email_sender.strip() and resolved_settings.email_password.strip())
    users = _sendable_users(resolved_service.store.list_users())
    for user in users:
        preferences = resolved_service.store.get_preferences(user.id)
        if not preferences.morning_email_enabled:
            skipped += 1
            continue
        if user.id in sent_users:
            skipped += 1
            continue
        brief = await resolved_service.morning_email_preview(
            user.id,
            (base_url or resolved_settings.morning_email_base_url).rstrip("/"),
        )
        receivers = _receiver_list(resolved_settings.email_receivers) or [brief.recipient]
        if not configured:
            failed += 1
            attempts.append(EmailAttempt(user.id, ",".join(receivers), False, "邮箱 SMTP 未配置"))
            continue
        ok = True
        detail_parts: list[str] = []
        for receiver in receivers:
            result = _send_email(
                brief,
                settings=resolved_settings,
                receiver=receiver,
                dry_run=dry_run,
            )
            ok = ok and result.ok
            detail_parts.append(result.detail)
        if ok:
            sent += 1
            attempts.append(EmailAttempt(user.id, ",".join(receivers), True, "; ".join(detail_parts)))
            if not dry_run:
                _mark_sent(state_path, today, user.id)
        else:
            failed += 1
            attempts.append(EmailAttempt(user.id, ",".join(receivers), False, "; ".join(detail_parts)))
    return DispatchSummary(sent=sent, skipped=skipped, failed=failed, attempts=attempts)


@dataclass(frozen=True)
class SendEmailResult:
    ok: bool
    detail: str


def _send_email(
    brief: MorningEmailBrief,
    *,
    settings: Settings,
    receiver: str,
    dry_run: bool,
) -> SendEmailResult:
    if dry_run:
        return SendEmailResult(True, "dry-run")
    host, port, tls = _resolve_smtp_settings(settings)
    sender = settings.email_sender.strip()
    from_addr = settings.email_from.strip() or sender
    message = MIMEMultipart("alternative")
    message["Subject"] = str(Header(brief.subject, "utf-8"))
    message["From"] = formataddr((str(Header(settings.email_sender_name, "utf-8")), from_addr))
    message["To"] = receiver
    message.attach(MIMEText(brief.text, "plain", "utf-8"))
    message.attach(MIMEText(brief.html, "html", "utf-8"))
    try:
        if tls == "ssl":
            with smtplib.SMTP_SSL(host, port, timeout=30) as server:
                server.login(sender, settings.email_password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                if tls != "none":
                    server.starttls(context=ssl.create_default_context())
                server.login(sender, settings.email_password)
                server.send_message(message)
    except Exception as exc:  # noqa: BLE001 - surface provider-specific SMTP failures in systemd logs.
        return SendEmailResult(False, f"send failed: {exc.__class__.__name__}")
    return SendEmailResult(True, "sent")


def _resolve_smtp_settings(settings: Settings) -> tuple[str, int, str]:
    tls = (settings.smtp_tls or "auto").strip().lower()
    if tls in {"true", "yes", "starttls", "tls"}:
        tls = "starttls"
    elif tls in {"ssl", "smtps"}:
        tls = "ssl"
    elif tls in {"none", "false", "off", "plain"}:
        tls = "none"
    else:
        tls = "auto"
    if settings.smtp_host.strip():
        resolved_tls = "ssl" if tls == "auto" and settings.smtp_port == 465 else tls
        if resolved_tls == "auto":
            resolved_tls = "starttls"
        return settings.smtp_host.strip(), settings.smtp_port or (465 if resolved_tls == "ssl" else 587), resolved_tls
    domain = settings.email_sender.split("@")[-1].lower()
    return SMTP_CONFIGS.get(domain, (f"smtp.{domain}", 465, "ssl"))


def _receiver_list(value: str) -> list[str]:
    return [item.strip() for chunk in value.replace(";", ",").split(",") for item in [chunk] if item.strip()]


def _sendable_users(users: list[UserAccount]) -> list[UserAccount]:
    sendable: list[UserAccount] = []
    for user in users:
        email = user.email.strip().lower()
        if not _looks_like_real_receiver(email):
            continue
        sendable.append(user)
    return sendable


def _looks_like_real_receiver(email: str) -> bool:
    if email.endswith("@marketdesk.local") or email.endswith("@example.com"):
        return False
    if email.startswith(("codex-", "smoke-")):
        return False
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", email))


def _load_sent_state(path: Path) -> dict[str, list[int]]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    state: dict[str, list[int]] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, list):
            state[key] = [int(item) for item in value if isinstance(item, int | str)]
    return state


def _mark_sent(path: Path, today: str, user_id: int) -> None:
    state = _load_sent_state(path)
    users = set(state.get(today, []))
    users.add(user_id)
    state[today] = sorted(users)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = asyncio.run(
        dispatch_morning_emails(
            base_url=args.base_url or None,
            dry_run=args.dry_run,
            force=args.force,
        )
    )
    print(summary.to_markdown(), end="")
    return 0 if summary.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
