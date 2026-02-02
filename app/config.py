from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SENTIENCEX_", case_sensitive=False)

    data_dir: Path = Field(default=Path("./data"))
    locale: str = Field(default="en")

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    trusted_hosts: List[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    rate_limit_enabled: bool = Field(default=True)
    rate_limit_rpm: int = Field(default=60)
    redis_url: str = Field(default="redis://localhost:6379/0")

    training_enabled: bool = Field(default=True)
    training_train_dir: Path = Field(default=Path("./TRAIN"))
    training_run_on_startup: bool = Field(default=False)
    training_nightly: bool = Field(default=False)
    training_nightly_hour: int = Field(default=3)
    training_nightly_minute: int = Field(default=15)

    stm_turns: int = Field(default=18)
    max_reply_chars: int = Field(default=800)

    proactive_min_turn_gap: int = Field(default=6)
    proactive_min_hours_gap: int = Field(default=12)

    distress_hidden_threshold: float = Field(default=0.62)
    threat_threshold: float = Field(default=0.70)

    templates_dir_name: str = Field(default="templates")
    lexicons_dir_name: str = Field(default="lexicons")

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
