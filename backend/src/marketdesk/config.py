from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MARKETDESK_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    frontend_dist: Path = Path("../frontend/dist")
    iwencai_api_key: str | None = None

    @property
    def database_path(self) -> Path:
        return self.data_dir / "marketdesk.db"
