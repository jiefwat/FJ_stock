from __future__ import annotations

import json
import smtplib
import ssl
from dataclasses import dataclass
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from html import escape
from typing import Literal
from urllib.request import Request, urlopen

from .config import get_settings

SMTP_CONFIGS = {
    "qq.com": ("smtp.qq.com", 465, True),
    "foxmail.com": ("smtp.qq.com", 465, True),
    "163.com": ("smtp.163.com", 465, True),
    "126.com": ("smtp.126.com", 465, True),
    "gmail.com": ("smtp.gmail.com", 587, False),
    "outlook.com": ("smtp-mail.outlook.com", 587, False),
    "hotmail.com": ("smtp-mail.outlook.com", 587, False),
    "live.com": ("smtp-mail.outlook.com", 587, False),
}


@dataclass(frozen=True)
class DispatchItem:
    channel: str
    ok: bool
    detail: str
    dry_run: bool = False


@dataclass(frozen=True)
class PreparedChannelMessage:
    channel: str
    subject: str
    text: str
    style: str
    html: str | None = None


@dataclass(frozen=True)
class DispatchResult:
    ok: bool
    items: list[DispatchItem]
    markdown: str


def dispatch_report(
    content: str,
    *,
    channels: list[str],
    subject: str = "StockTS 每日复盘",
    dry_run: bool = False,
    style: str = "auto",
) -> DispatchResult:
    settings = get_settings()
    items: list[DispatchItem] = []
    for channel in channels:
        normalized = channel.strip().lower()
        if not normalized:
            continue
        prepared = prepare_channel_message(
            content,
            channel=normalized,
            subject=subject,
            style=style,
        )
        if normalized == "email":
            items.append(
                _send_email(
                    prepared,
                    sender=settings.email_sender,
                    from_addr=settings.email_from or settings.email_sender,
                    password=settings.email_password,
                    receivers=settings.email_receivers,
                    sender_name=settings.email_sender_name,
                    smtp_host=settings.smtp_host,
                    smtp_port=settings.smtp_port,
                    smtp_tls=settings.smtp_tls,
                    dry_run=dry_run,
                )
            )
        elif normalized in {"wechat", "wecom", "企业微信", "微信"}:
            items.append(
                _send_wechat(
                    prepared,
                    webhook_url=settings.wechat_webhook_url,
                    msg_type=settings.wechat_msg_type,
                    max_bytes=settings.wechat_max_bytes,
                    dry_run=dry_run,
                )
            )
        elif normalized in {"feishu", "飞书"}:
            items.append(
                _send_feishu(
                    prepared,
                    webhook_url=settings.feishu_webhook_url,
                    dry_run=dry_run,
                )
            )
        else:
            items.append(
                DispatchItem(
                    normalized,
                    False,
                    f"unsupported channel style={prepared.style}",
                    dry_run=dry_run,
                )
            )

    ok = bool(items) and all(item.ok for item in items)
    lines = ["# StockTS 发送结果", ""]
    for item in items:
        mark = "OK" if item.ok else "FAIL"
        lines.append(f"- {mark} {item.channel}: {item.detail}")
    return DispatchResult(ok=ok, items=items, markdown="\n".join(lines) + "\n")


def _send_email(
    prepared: PreparedChannelMessage,
    *,
    sender: str,
    from_addr: str,
    password: str,
    receivers: list[str],
    sender_name: str,
    smtp_host: str = "",
    smtp_port: int = 0,
    smtp_tls: str = "auto",
    dry_run: bool,
) -> DispatchItem:
    configured = bool(sender.strip() and password.strip())
    if dry_run:
        detail = "dry-run configured" if configured else "dry-run not configured"
        return DispatchItem("email", True, f"{detail} style={prepared.style}", dry_run=True)
    if not configured:
        return DispatchItem(
            "email",
            False,
            f"缺少邮箱账号或授权码 style={prepared.style}",
        )
    resolved_receivers = receivers or [sender]
    smtp_server, resolved_port, tls_mode = _resolve_smtp_settings(
        sender,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_tls=smtp_tls,
    )

    message = MIMEMultipart("alternative")
    message["Subject"] = Header(prepared.subject, "utf-8")
    message["From"] = formataddr((str(Header(sender_name, "utf-8")), from_addr or sender))
    message["To"] = ", ".join(resolved_receivers)
    message.attach(MIMEText(prepared.text, "plain", "utf-8"))
    message.attach(MIMEText(prepared.html or _markdown_to_html(prepared.text), "html", "utf-8"))

    try:
        if tls_mode == "ssl":
            with smtplib.SMTP_SSL(smtp_server, resolved_port, timeout=30) as server:
                server.login(sender, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(smtp_server, resolved_port, timeout=30) as server:
                if tls_mode != "none":
                    server.starttls(context=ssl.create_default_context())
                server.login(sender, password)
                server.send_message(message)
    except Exception as exc:
        return DispatchItem(
            "email",
            False,
            f"send failed: {exc.__class__.__name__} style={prepared.style}",
        )
    return DispatchItem(
        "email",
        True,
        f"sent to {len(resolved_receivers)} receiver(s) style={prepared.style}",
    )


def _resolve_smtp_settings(
    sender: str,
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_tls: str,
) -> tuple[str, int, str]:
    tls = (smtp_tls or "auto").strip().lower()
    if tls in {"true", "yes", "starttls", "tls"}:
        tls = "starttls"
    elif tls in {"ssl", "smtps"}:
        tls = "ssl"
    elif tls in {"none", "false", "off", "plain"}:
        tls = "none"
    else:
        tls = "auto"
    if smtp_host.strip():
        if tls == "auto":
            tls = "ssl" if smtp_port == 465 else "starttls"
        return smtp_host.strip(), smtp_port or (465 if tls == "ssl" else 587), tls
    domain = sender.split("@")[-1].lower()
    server, port, use_ssl = SMTP_CONFIGS.get(domain, (f"smtp.{domain}", 465, True))
    return server, port, "ssl" if use_ssl else "starttls"


def _send_wechat(
    prepared: PreparedChannelMessage,
    *,
    webhook_url: str,
    msg_type: str,
    max_bytes: int,
    dry_run: bool,
) -> DispatchItem:
    configured = bool(webhook_url.strip())
    if dry_run:
        detail = "dry-run configured" if configured else "dry-run not configured"
        return DispatchItem("wechat", True, f"{detail} style={prepared.style}", dry_run=True)
    if not configured:
        return DispatchItem(
            "wechat",
            False,
            f"WECHAT_WEBHOOK_URL missing style={prepared.style}",
        )

    chunks = _chunk_by_utf8_bytes(prepared.text, max_bytes=max_bytes)
    ok_count = 0
    for chunk in chunks:
        payload = (
            {"msgtype": "text", "text": {"content": chunk}}
            if msg_type == "text"
            else {"msgtype": "markdown", "markdown": {"content": chunk}}
        )
        request = Request(
            webhook_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:  # noqa: S310 - user-configured webhook
                body = json.loads(response.read().decode("utf-8"))
                if body.get("errcode") == 0:
                    ok_count += 1
        except Exception as exc:
            return DispatchItem(
                "wechat",
                False,
                f"send failed: {exc.__class__.__name__} style={prepared.style}",
            )
    return DispatchItem(
        "wechat",
        ok_count == len(chunks),
        f"sent {ok_count}/{len(chunks)} chunk(s) style={prepared.style}",
    )


def _send_feishu(
    prepared: PreparedChannelMessage,
    *,
    webhook_url: str,
    dry_run: bool,
) -> DispatchItem:
    configured = bool(webhook_url.strip())
    if dry_run:
        detail = "dry-run configured" if configured else "dry-run not configured"
        return DispatchItem("feishu", True, f"{detail} style={prepared.style}", dry_run=True)
    if not configured:
        return DispatchItem(
            "feishu",
            False,
            f"FEISHU_WEBHOOK_URL missing style={prepared.style}",
        )

    payload = {
        "msg_type": "text",
        "content": {
            "text": prepared.text,
        },
    }
    request = Request(
        webhook_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - user-configured webhook
            body = json.loads(response.read().decode("utf-8"))
            ok = body.get("StatusCode", 0) in {0, "0"} or body.get("code", 0) in {0, "0"}
    except Exception as exc:
        return DispatchItem(
            "feishu",
            False,
            f"send failed: {exc.__class__.__name__} style={prepared.style}",
        )
    return DispatchItem("feishu", ok, f"sent style={prepared.style}")


def prepare_channel_message(
    content: str,
    *,
    channel: str,
    subject: str,
    style: str = "auto",
) -> PreparedChannelMessage:
    normalized = channel.strip().lower()
    resolved_style = _resolve_style(normalized, style)
    if resolved_style == "full":
        text = content.strip()
    elif resolved_style == "action":
        text = _action_digest(content)
    else:
        text = _digest_report(content)
    html = _render_email_report_html(subject, text) if normalized == "email" else None
    return PreparedChannelMessage(
        channel=normalized,
        subject=subject,
        text=text,
        style=resolved_style,
        html=html,
    )


def _resolve_style(channel: str, style: str) -> Literal["full", "digest", "action"]:
    normalized = style.strip().lower() or "auto"
    if channel == "email":
        return "full"
    if normalized in {"full", "digest", "action"}:
        return normalized  # type: ignore[return-value]
    return "digest"


def _digest_report(content: str) -> str:
    picked: list[str] = []
    current_section = ""
    section_hits = {"## 今日一句话", "## 最需要关注的 3 件事", "## 持仓风险 Top 3", "## 明日观察"}
    for line in content.splitlines():
        if line.startswith("# "):
            if not picked:
                picked.append(line)
            continue
        if line.startswith("## "):
            current_section = line
        if current_section in section_hits:
            if line.strip():
                picked.append(line)
        if len("\n".join(picked).encode("utf-8")) >= 2800:
            break
    text = "\n".join(picked).strip()
    return text or content.strip()


def _action_digest(content: str) -> str:
    markers = ("# ", "## ", "-", "1.", "2.", "3.")
    lines = [line for line in _digest_report(content).splitlines() if line.startswith(markers)]
    return "\n".join(lines[:14]).strip() or content.strip()


def _render_email_report_html(subject: str, content: str) -> str:
    body = []
    for line in content.splitlines():
        if line.startswith("# "):
            body.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{escape(line[3:])}</h2>")
        elif line[:2].isdigit() and line[1] == ".":
            body.append(f"<p><strong>{escape(line[:2])}</strong> {escape(line[3:])}</p>")
        elif line.startswith("- "):
            body.append(f"<p>• {escape(line[2:])}</p>")
        elif line:
            body.append(f"<p>{escape(line)}</p>")
    return (
        "<html><body style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
        'color:#102033;background:#f4f7fa;padding:24px;">'
        '<div style="max-width:760px;margin:0 auto;background:#ffffff;border:1px solid #d7e2ea;'
        'border-radius:18px;padding:28px;">'
        '<div style="font-size:12px;letter-spacing:.08em;color:#6b7c8c;'
        f'text-transform:uppercase;">{escape(subject)}</div>'
        + "".join(body)
        + "</div></body></html>"
    )


def _chunk_by_utf8_bytes(content: str, *, max_bytes: int) -> list[str]:
    limit = max(512, max_bytes)
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for line in content.splitlines():
        line_size = len((line + "\n").encode("utf-8"))
        if current and current_size + line_size > limit:
            chunks.append("\n".join(current))
            current = []
            current_size = 0
        current.append(line)
        current_size += line_size
    if current:
        chunks.append("\n".join(current))
    return chunks or [content]


def _markdown_to_html(markdown: str) -> str:
    lines = []
    for line in markdown.splitlines():
        if line.startswith("# "):
            lines.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("## "):
            lines.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("- "):
            lines.append(f"<p>{escape(line)}</p>")
        else:
            lines.append(f"<p>{escape(line)}</p>" if line else "<br />")
    return "<html><body>" + "\n".join(lines) + "</body></html>"
