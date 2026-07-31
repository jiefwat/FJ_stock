from pathlib import Path

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
        validation_alias=AliasChoices("MARKETDESK_LLM_WEB_API_KEY", "DASHSCOPE_API_KEY"),
    )
    llm_web_base_url: str = "https://api.openai.com/v1"
    llm_web_model: str = "gpt-4.1-mini"
    auto_refresh_enabled: bool = True
    auto_refresh_interval_seconds: float = 7200
    auto_refresh_run_immediately: bool = True

    @property
    def database_path(self) -> Path:
        return self.data_dir / "marketdesk.db"
