from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MARKETDESK_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    data_dir: Path = Path("data")
    frontend_dist: Path = Path("../frontend/dist")
    iwencai_api_key: str | None = None
    iwencai_endpoint: str | None = None
    llm_web_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "MARKETDESK_FINANCIAL_LLM_API_KEY",
            "MARKETDESK_LLM_WEB_API_KEY",
            "DASHSCOPE_API_KEY",
        ),
    )
    llm_web_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices(
            "MARKETDESK_FINANCIAL_LLM_BASE_URL", "MARKETDESK_LLM_WEB_BASE_URL"
        ),
    )
    llm_web_model: str = Field(
        default="gpt-4.1-mini",
        validation_alias=AliasChoices(
            "MARKETDESK_FINANCIAL_LLM_MODEL", "MARKETDESK_LLM_WEB_MODEL"
        ),
    )
    llm_web_api_style: Literal["auto", "responses", "chat_completions"] = Field(
        default="auto",
        validation_alias=AliasChoices(
            "MARKETDESK_FINANCIAL_LLM_API_STYLE", "MARKETDESK_LLM_WEB_API_STYLE"
        ),
    )
    llm_web_search_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "MARKETDESK_FINANCIAL_LLM_WEB_SEARCH_ENABLED",
            "MARKETDESK_LLM_WEB_SEARCH_ENABLED",
        ),
    )
    auto_refresh_enabled: bool = True
    auto_refresh_interval_seconds: float = 600
    auto_refresh_run_immediately: bool = True
    morning_email_base_url: str = "https://stock.jiewat-kaka-fj.com"
    email_sender: str = Field(
        default="",
        validation_alias=AliasChoices("MARKETDESK_EMAIL_SENDER", "EMAIL_SENDER", "SMTP_USER"),
    )
    email_from: str = Field(
        default="",
        validation_alias=AliasChoices("MARKETDESK_EMAIL_FROM", "SMTP_FROM", "EMAIL_SENDER"),
    )
    email_sender_name: str = Field(
        default="StockTS 股票分析助手",
        validation_alias=AliasChoices("MARKETDESK_EMAIL_SENDER_NAME", "EMAIL_SENDER_NAME"),
    )
    email_password: str = Field(
        default="",
        validation_alias=AliasChoices("MARKETDESK_EMAIL_PASSWORD", "EMAIL_PASSWORD", "SMTP_PASSWORD"),
    )
    email_receivers: str = Field(
        default="",
        validation_alias=AliasChoices("MARKETDESK_EMAIL_RECEIVERS", "EMAIL_RECEIVERS"),
    )
    smtp_host: str = Field(
        default="",
        validation_alias=AliasChoices("MARKETDESK_SMTP_HOST", "SMTP_HOST"),
    )
    smtp_port: int = Field(
        default=0,
        validation_alias=AliasChoices("MARKETDESK_SMTP_PORT", "SMTP_PORT"),
    )
    smtp_tls: str = Field(
        default="auto",
        validation_alias=AliasChoices("MARKETDESK_SMTP_TLS", "SMTP_TLS"),
    )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "marketdesk.db"
