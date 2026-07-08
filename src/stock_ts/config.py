from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_id: str = "stock-ts"
    app_env: str = "local"
    log_level: str = "INFO"
    provider: str = "auto"
    holdings_path: str = "data/portfolio/holdings.csv"
    cache_dir: str = "data/cache"
    tushare_token: str = ""
    itick_api_key: str = ""
    email_sender: str = ""
    email_from: str = ""
    email_sender_name: str = "StockTS 股票分析助手"
    email_password: str = ""
    email_receivers: list[str] | None = None
    smtp_host: str = ""
    smtp_port: int = 0
    smtp_tls: str = "auto"
    wechat_webhook_url: str = ""
    feishu_webhook_url: str = ""
    wechat_msg_type: str = "markdown"
    wechat_max_bytes: int = 4000
    notification_report_channels: list[str] | None = None
    notification_report_style: str = "auto"
    llm_provider: str = "openai-compatible"
    llm_api_key: str = ""
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen-plus"
    llm_temperature: float = 0.2
    llm_timeout: int = 30

    @property
    def has_tushare_token(self) -> bool:
        return bool(self.tushare_token.strip())

    @property
    def has_itick_api_key(self) -> bool:
        return bool(self.itick_api_key.strip())

    @property
    def has_llm_api_key(self) -> bool:
        return bool(self.llm_api_key.strip())

    def safe_summary(self) -> dict[str, str]:
        return {
            "app_id": self.app_id,
            "app_env": self.app_env,
            "log_level": self.log_level,
            "provider": self.provider,
            "holdings_path": self.holdings_path,
            "cache_dir": self.cache_dir,
            "tushare_token": "configured" if self.has_tushare_token else "missing",
            "itick": "configured" if self.has_itick_api_key else "missing",
            "email": "configured" if self.email_sender and self.email_password else "missing",
            "wechat": "configured" if self.wechat_webhook_url else "missing",
            "feishu": "configured" if self.feishu_webhook_url else "missing",
            "notification_report_channels": ",".join(self.notification_report_channels or []),
            "notification_report_style": self.notification_report_style,
            "llm": "configured" if self.has_llm_api_key else "missing",
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
        }


def load_dotenv_values(path: str | Path = ".env") -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def save_dotenv_values(
    values: dict[str, str],
    *,
    path: str | Path = ".env",
    merge: bool = True,
) -> Path:
    env_path = Path(path)
    existing = load_dotenv_values(env_path) if merge else {}
    merged = existing.copy()
    merged.update(values)

    order = [
        "APP_ID",
        "APP_ENV",
        "LOG_LEVEL",
        "STOCK_TS_PROVIDER",
        "STOCK_TS_HOLDINGS_PATH",
        "STOCK_TS_CACHE_DIR",
        "TUSHARE_TOKEN",
        "ITICK_API_KEY",
        "EMAIL_SENDER",
        "SMTP_USER",
        "SMTP_FROM",
        "EMAIL_SENDER_NAME",
        "EMAIL_PASSWORD",
        "SMTP_PASSWORD",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_TLS",
        "EMAIL_RECEIVERS",
        "WECHAT_WEBHOOK_URL",
        "FEISHU_WEBHOOK_URL",
        "WECHAT_MSG_TYPE",
        "WECHAT_MAX_BYTES",
        "NOTIFICATION_REPORT_CHANNELS",
        "NOTIFICATION_REPORT_STYLE",
        "STOCK_TS_LLM_PROVIDER",
        "STOCK_TS_LLM_API_KEY",
        "DASHSCOPE_API_KEY",
        "STOCK_TS_LLM_BASE_URL",
        "STOCK_TS_LLM_MODEL",
        "STOCK_TS_LLM_TEMPERATURE",
        "STOCK_TS_LLM_TIMEOUT",
    ]
    keys = [key for key in order if key in merged] + [key for key in merged if key not in order]
    lines = [f"{key}={_serialize_env_value(merged[key])}" for key in keys]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path


def _serialize_env_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _value(key: str, dotenv: dict[str, str], default: str) -> str:
    return os.getenv(key) or dotenv.get(key) or default


def _first_value(keys: list[str], dotenv: dict[str, str], default: str) -> str:
    for key in keys:
        value = os.getenv(key) or dotenv.get(key)
        if value:
            return value
    return default


def get_settings(env_file: str | Path = ".env") -> Settings:
    dotenv = load_dotenv_values(env_file)
    return Settings(
        app_id=_value("APP_ID", dotenv, "stock-ts"),
        app_env=_value("APP_ENV", dotenv, "local"),
        log_level=_value("LOG_LEVEL", dotenv, "INFO"),
        provider=_value("STOCK_TS_PROVIDER", dotenv, "auto"),
        holdings_path=_value("STOCK_TS_HOLDINGS_PATH", dotenv, "data/portfolio/holdings.csv"),
        cache_dir=_value("STOCK_TS_CACHE_DIR", dotenv, "data/cache"),
        tushare_token=_value("TUSHARE_TOKEN", dotenv, ""),
        itick_api_key=_value("ITICK_API_KEY", dotenv, ""),
        email_sender=_first_value(["EMAIL_SENDER", "SMTP_USER", "SMTP_FROM"], dotenv, ""),
        email_from=_first_value(["SMTP_FROM", "EMAIL_SENDER", "SMTP_USER"], dotenv, ""),
        email_sender_name=_value("EMAIL_SENDER_NAME", dotenv, "StockTS 股票分析助手"),
        email_password=_first_value(["EMAIL_PASSWORD", "SMTP_PASSWORD"], dotenv, ""),
        email_receivers=[
            item.strip()
            for item in _value("EMAIL_RECEIVERS", dotenv, "").split(",")
            if item.strip()
        ],
        smtp_host=_value("SMTP_HOST", dotenv, ""),
        smtp_port=int(_value("SMTP_PORT", dotenv, "0") or "0"),
        smtp_tls=_value("SMTP_TLS", dotenv, "auto").lower(),
        wechat_webhook_url=_value("WECHAT_WEBHOOK_URL", dotenv, ""),
        feishu_webhook_url=_value("FEISHU_WEBHOOK_URL", dotenv, ""),
        wechat_msg_type=_value("WECHAT_MSG_TYPE", dotenv, "markdown").lower(),
        wechat_max_bytes=int(_value("WECHAT_MAX_BYTES", dotenv, "4000") or "4000"),
        notification_report_channels=[
            item.strip()
            for item in _value("NOTIFICATION_REPORT_CHANNELS", dotenv, "email,wechat").split(",")
            if item.strip()
        ],
        notification_report_style=_value("NOTIFICATION_REPORT_STYLE", dotenv, "auto").lower(),
        llm_provider=_value("STOCK_TS_LLM_PROVIDER", dotenv, "openai-compatible"),
        llm_api_key=_first_value(["STOCK_TS_LLM_API_KEY", "DASHSCOPE_API_KEY"], dotenv, ""),
        llm_base_url=_value(
            "STOCK_TS_LLM_BASE_URL",
            dotenv,
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        llm_model=_value("STOCK_TS_LLM_MODEL", dotenv, "qwen-plus"),
        llm_temperature=float(_value("STOCK_TS_LLM_TEMPERATURE", dotenv, "0.2") or "0.2"),
        llm_timeout=int(_value("STOCK_TS_LLM_TIMEOUT", dotenv, "30") or "30"),
    )
