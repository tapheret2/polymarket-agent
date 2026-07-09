from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    polymarket_gamma_url: str = "https://gamma-api.polymarket.com"
    polymarket_user_agent: str = (
        "polymarket-agent/0.1 (+https://github.com/tapheret2/polymarket-agent; research)"
    )
    paper_bankroll: float = 1000.0
    min_liquidity: float = 1000.0
    scan_limit: int = 50
    request_timeout: float = 30.0
    data_dir: Path = ROOT / "data"
    paper_book_path: Path = ROOT / "data" / "processed" / "paper_book.json"


def get_settings() -> Settings:
    return Settings()
