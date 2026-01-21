"""
Application configuration using Pydantic Settings.
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Daňový Poradce Pro"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./data/app.db"
    database_encryption_key: Optional[str] = None

    # API
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Claude AI
    anthropic_api_key: Optional[str] = None
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 4096

    # JWT Authentication
    jwt_secret: str = "change-this-in-production-use-strong-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    # App Store Connect (optional)
    appstore_key_id: Optional[str] = None
    appstore_issuer_id: Optional[str] = None
    appstore_private_key_path: Optional[Path] = None

    # Memory System
    memory_dir: Path = Path(".agent-memory")

    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    data_dir: Path = base_dir / "data"
    knowledge_base_dir: Path = base_dir / "knowledge_base"

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
