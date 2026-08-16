from __future__ import annotations

import asyncio
import re
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from html import escape

from marketdesk.config import Settings
from marketdesk.models import DecisionEvent, UserAccount
from marketdesk.store import Store


@dataclass(frozen=True)
class DecisionEmailSummary:
    sent: int = 0
    failed: int = 0
    skipped: int = 0


async def dispatch_decision_emails(
    store: Store, settings: Settings | None = None
) -> DecisionEmailSummary:
    resolved = settings or Settings()
    sent = 0
    failed = 0
    skipped = 0
    for account, event in store.list_pending_decision_emails():
        receivers = _receiver_list(resolved.email_receivers) or [account.email]
        receivers = [receiver for receiver in receivers if _looks_like_real_receiver(receiver)]
        if not receivers:
            store.abandon_decision_email(event.id, "recipient unavailable")
            skipped += 1
            continue
        if not resolved.email_sender.strip() or not resolved.email_password.strip():
            store.mark_decision_email_result(event.id, sent=False, error="SMTP not configured")
            failed += 1
            continue
        try:
            for receiver in receivers:
                message = _build_message(account, event, receiver, resolved)
                await asyncio.to_thread(_send_message, message, resolved)
        except Exception as error:  # noqa: BLE001 - persist only the bounded error class.
            store.mark_decision_email_result(
                event.id, sent=False, error=error.__class__.__name__
            )
            failed += 1
            continue
        store.mark_decision_email_result(event.id, sent=True)
        sent += 1
    return DecisionEmailSummary(sent=sent, failed=failed, skipped=skipped)


def _build_message(
    account: UserAccount, event: DecisionEvent, receiver: str, settings: Settings
) -> EmailMessage:
    url = f"{settings.morning_email_base_url.rstrip('/')}/#{event.href}"
    subject = f"[StockTS] {event.name}：{event.action}"
    text = (
        f"{account.display_name}，系统监控到持仓决定发生变化。\n\n"
        f"股票：{event.name}（{event.symbol}）\n"
        f"现在：{event.action}\n"
        f"之前：{event.previous_action}\n"
        f"原因：{event.summary}\n"
        f"时间：{event.observed_at.astimezone().strftime('%Y-%m-%d %H:%M')}\n"
        f"查看：{url}\n\n"
        "本邮件只提醒研究决定变化，不会自动执行交易。"
    )
    html = (
        "<html><body>"
        f"<p>{escape(account.display_name)}，系统监控到持仓决定发生变化。</p>"
        f"<h2>{escape(event.name)}：{escape(event.action)}</h2>"
        f"<p>之前：{escape(event.previous_action)}</p>"
        f"<p>原因：{escape(event.summary)}</p>"
        f'<p><a href="{escape(url)}">查看完整决定</a></p>'
        "<p><small>本邮件只提醒研究决定变化，不会自动执行交易。</small></p>"
        "</body></html>"
    )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.email_from.strip() or settings.email_sender.strip()
    message["To"] = receiver
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return message


def _send_message(message: EmailMessage, settings: Settings) -> None:
    host, port, tls = _resolve_smtp_settings(settings)
    if tls == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=30) as server:
            server.login(settings.email_sender, settings.email_password)
            server.send_message(message)
        return
    with smtplib.SMTP(host, port, timeout=30) as server:
        if tls != "none":
            server.starttls(context=ssl.create_default_context())
        server.login(settings.email_sender, settings.email_password)
        server.send_message(message)


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
        return (
            settings.smtp_host.strip(),
            settings.smtp_port or (465 if resolved_tls == "ssl" else 587),
            resolved_tls,
        )
    domain = settings.email_sender.split("@")[-1].lower()
    defaults = {
        "qq.com": ("smtp.qq.com", 465, "ssl"),
        "foxmail.com": ("smtp.qq.com", 465, "ssl"),
        "163.com": ("smtp.163.com", 465, "ssl"),
        "126.com": ("smtp.126.com", 465, "ssl"),
        "gmail.com": ("smtp.gmail.com", 587, "starttls"),
        "outlook.com": ("smtp-mail.outlook.com", 587, "starttls"),
    }
    return defaults.get(domain, (f"smtp.{domain}", 465, "ssl"))


def _receiver_list(value: str) -> list[str]:
    return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]


def _looks_like_real_receiver(email: str) -> bool:
    normalized = email.strip().lower()
    if normalized.endswith(("@marketdesk.local", "@example.com", ".test")):
        return False
    if normalized.startswith(("codex-", "smoke-")):
        return False
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", normalized))
