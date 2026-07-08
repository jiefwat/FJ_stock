import os
import sys
from pathlib import Path
from subprocess import run

from stock_ts.imports import load_price_bars_csv
from stock_ts.notification import dispatch_report, prepare_channel_message
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.workflows import (
    build_daily_report,
    build_imported_stock_markdown,
    build_news_markdown,
)


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return env


def write_price_csv(path: Path) -> None:
    path.write_text(
        "date,open,high,low,close,volume\n"
        "2026-06-01,10,10.5,9.8,10.2,1000\n"
        "2026-06-02,10.2,10.8,10.1,10.7,1200\n"
        "2026-06-03,10.7,11.2,10.5,11.0,1600\n"
        "2026-06-04,11.0,11.4,10.9,11.3,1800\n"
        "2026-06-05,11.3,11.8,11.1,11.6,2200\n",
        encoding="utf-8",
    )


def write_news_csv(path: Path) -> None:
    path.write_text(
        "date,source,title,summary,url,sentiment\n"
        "2026-06-05,示例财经,半导体景气改善,订单增长和国产替代推进,https://example.com/a,positive\n"
        "2026-06-05,示例公告,白酒板块需求承压,渠道库存压力仍需消化,https://example.com/b,negative\n",
        encoding="utf-8",
    )


def test_imported_price_csv_can_drive_stock_analysis(tmp_path: Path) -> None:
    price_file = tmp_path / "prices.csv"
    write_price_csv(price_file)

    bars = load_price_bars_csv(price_file)
    report = build_imported_stock_markdown(price_file, code="688001", name="示例科技")

    assert len(bars) == 5
    assert report.title == "导入行情分析：示例科技"
    assert "# 个股分析：示例科技（688001）" in report.markdown
    assert "最新收盘：11.60" in report.markdown


def test_news_csv_can_be_rendered_and_embedded_in_daily_report(tmp_path: Path) -> None:
    news_file = tmp_path / "news.csv"
    write_news_csv(news_file)

    news = build_news_markdown(news_file)
    daily = build_daily_report(
        SampleDataProvider(),
        holdings_path="data/portfolio/holdings.csv",
        news_path=news_file,
    )

    assert "# 新闻舆情摘要" in news.markdown
    assert "半导体景气改善" in news.markdown
    assert "## 新闻舆情摘要" in daily.markdown
    assert "白酒板块需求承压" in daily.markdown


def test_notification_dispatch_supports_dry_run_without_secrets() -> None:
    result = dispatch_report(
        "# StockTS 每日复盘\n内容",
        channels=["email", "wechat", "feishu"],
        subject="StockTS 测试",
        dry_run=True,
        style="digest",
    )

    assert result.ok
    assert [item.channel for item in result.items] == ["email", "wechat", "feishu"]
    assert all(item.dry_run for item in result.items)
    assert all("configured" in item.detail or "dry-run" in item.detail for item in result.items)
    assert all("style=" in item.detail for item in result.items)


def test_email_dispatch_explains_missing_password_without_secret_values(monkeypatch) -> None:
    for key in ["SMTP_USER", "SMTP_FROM", "SMTP_PASSWORD", "EMAIL_SENDER", "EMAIL_PASSWORD"]:
        monkeypatch.delenv(key, raising=False)
    result = dispatch_report(
        "# StockTS 每日复盘\n内容",
        channels=["email"],
        subject="StockTS 测试",
        dry_run=False,
        style="full",
    )

    assert not result.ok
    assert "缺少邮箱账号或授权码" in result.items[0].detail
    assert "secret" not in result.items[0].detail.lower()


def test_prepare_channel_message_uses_channel_profiles() -> None:
    content = (
        "# StockTS 每日复盘（2026-06-05）\n\n"
        "## 今日一句话\n"
        "- 市场偏强，但高位分歧扩大。\n\n"
        "## 最需要关注的 3 件事\n"
        "1. 看成交额是否持续放大\n"
        "2. 看主线板块是否扩散\n"
        "3. 看持仓龙头是否守住均线\n"
    )

    wechat = prepare_channel_message(content, channel="wechat", subject="测试", style="auto")
    email = prepare_channel_message(content, channel="email", subject="测试", style="auto")

    assert wechat.channel == "wechat"
    assert wechat.style == "digest"
    assert "今日一句话" in wechat.text
    assert len(wechat.text.encode("utf-8")) <= 4000
    assert email.style == "full"
    assert email.html is not None
    assert "<html>" in email.html


def test_cli_send_daily_dry_run_accepts_news_and_channels(tmp_path: Path) -> None:
    news_file = tmp_path / "news.csv"
    write_news_csv(news_file)

    result = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "send-daily",
            "--provider",
            "sample",
            "--holdings",
            "data/portfolio/holdings.csv",
            "--news",
            str(news_file),
            "--channels",
            "email,wechat,feishu",
            "--dry-run",
            "--style",
            "digest",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )

    assert result.returncode == 0
    assert "StockTS 发送结果" in result.stdout
    assert "email" in result.stdout
    assert "wechat" in result.stdout
    assert "feishu" in result.stdout
    assert "dry-run" in result.stdout
    assert "style=digest" in result.stdout


def test_cli_test_notify_dry_run_accepts_channel_and_style() -> None:
    result = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "test-notify",
            "--channel",
            "feishu",
            "--style",
            "digest",
            "--dry-run",
            "--subject",
            "StockTS 通知测试",
            "--content",
            "测试消息",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=cli_env(),
    )

    assert result.returncode == 0
    assert "StockTS 发送结果" in result.stdout
    assert "feishu" in result.stdout
    assert "style=digest" in result.stdout


def test_email_dispatch_uses_explicit_smtp_ssl(monkeypatch, tmp_path: Path) -> None:
    for key in [
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_TLS",
        "SMTP_USER",
        "SMTP_FROM",
        "SMTP_PASSWORD",
        "EMAIL_SENDER",
        "EMAIL_PASSWORD",
    ]:
        monkeypatch.delenv(key, raising=False)
    from stock_ts.config import save_dotenv_values

    env_file = tmp_path / ".env"
    save_dotenv_values(
        {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "465",
            "SMTP_TLS": "ssl",
            "SMTP_USER": "sender@example.com",
            "SMTP_FROM": "from@example.com",
            "SMTP_PASSWORD": "secret-password",
            "EMAIL_RECEIVERS": "to@example.com",
        },
        path=env_file,
        merge=False,
    )
    monkeypatch.chdir(tmp_path)
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append((host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def login(self, sender, password):
            assert sender == "sender@example.com"
            assert password == "secret-password"

        def send_message(self, message):
            assert message["To"] == "to@example.com"
            assert "from@example.com" in message["From"]

    monkeypatch.setattr("stock_ts.notification.smtplib.SMTP_SSL", FakeSMTP)

    result = dispatch_report(
        "# report",
        channels=["email"],
        subject="StockTS 测试",
        dry_run=False,
        style="digest",
    )

    assert result.ok
    assert calls == [("smtp.gmail.com", 465, 30)]
    assert "secret-password" not in result.markdown


def test_email_daily_report_uses_full_content_even_when_default_style_is_digest() -> None:
    from stock_ts.notification import prepare_channel_message

    content = (
        "# StockTS 每日复盘\n\n"
        "## 今日一句话\n只有标题是不够的。\n\n"
        "## A股大盘\n大盘分析正文。\n\n"
        "## 我的持仓\n持仓分析正文。\n"
    )

    prepared = prepare_channel_message(
        content,
        channel="email",
        subject="StockTS 早间复盘与机会（2026-06-26）",
        style="digest",
    )

    assert prepared.subject == "StockTS 早间复盘与机会（2026-06-26）"
    assert prepared.style == "full"
    assert "## A股大盘" in prepared.text
    assert "## 我的持仓" in prepared.text
    assert "持仓分析正文" in (prepared.html or "")
