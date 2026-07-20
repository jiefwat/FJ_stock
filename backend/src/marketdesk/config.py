from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MARKETDESK_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    frontend_dist: Path = Path("../frontend/dist")
    iwencai_api_key: str | None = None
    iwencai_endpoint: str | None = None
    auto_refresh_enabled: bool = True
    auto_refresh_interval_seconds: float = 7200
    auto_refresh_run_immediately: bool = True

    @property
    def database_path(self) -> Path:
        return self.data_dir / "marketdesk.db"
