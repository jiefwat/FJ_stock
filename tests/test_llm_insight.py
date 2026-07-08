import os
import sys
from pathlib import Path
from subprocess import run

from stock_ts.config import get_settings
from stock_ts.llm import (
    StaticChatClient,
    generate_stock_ai_insight,
)
from stock_ts.providers.sample import SampleDataProvider
from stock_ts.workflows import build_deep_stock_report


def cli_env(**overrides: str) -> dict[str, str]:
    env = os.environ.copy()
    repo_root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = str(repo_root / "src")
    for key in [
        "STOCK_TS_LLM_API_KEY",
        "DASHSCOPE_API_KEY",
        "STOCK_TS_LLM_BASE_URL",
        "STOCK_TS_LLM_MODEL",
    ]:
        env.pop(key, None)
    env.update(overrides)
    return env


def test_settings_reports_llm_configured_without_exposing_key(monkeypatch) -> None:
    monkeypatch.setenv("STOCK_TS_LLM_API_KEY", "sk-test-secret")
    monkeypatch.setenv("STOCK_TS_LLM_MODEL", "qwen-plus")

    settings = get_settings(env_file="/tmp/not-exists-stockts.env")

    assert settings.has_llm_api_key
    assert settings.safe_summary()["llm"] == "configured"
    assert "sk-test-secret" not in str(settings.safe_summary())


def test_ai_insight_disabled_without_key() -> None:
    report = build_deep_stock_report(SampleDataProvider(), "600519")

    insight = generate_stock_ai_insight(report, settings=get_settings(env_file="/tmp/not-exists"))

    assert not insight.enabled
    assert "AI 增强未启用" in insight.markdown
    assert "不构成投资建议" in insight.markdown


def test_ai_insight_uses_client_and_keeps_safety_disclaimer(monkeypatch) -> None:
    monkeypatch.setenv("STOCK_TS_LLM_API_KEY", "sk-test-secret")
    settings = get_settings(env_file="/tmp/not-exists")
    report = build_deep_stock_report(SampleDataProvider(), "600519")

    insight = generate_stock_ai_insight(
        report,
        settings=settings,
        client=StaticChatClient("AI 观点：保持观察，等待失效条件确认。"),
    )

    assert insight.enabled
    assert "AI 观点" in insight.markdown
    assert "不构成投资建议" in insight.markdown
    assert "sk-test-secret" not in insight.markdown


def test_cli_ai_insight_degrades_without_key(tmp_path: Path) -> None:
    result = run(
        [
            sys.executable,
            "-m",
            "stock_ts.cli",
            "ai-insight",
            "600519",
            "--provider",
            "sample",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
        env=cli_env(),
    )

    assert result.returncode == 0
    assert "AI 增强未启用" in result.stdout
    assert "不构成投资建议" in result.stdout
