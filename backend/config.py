from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # SQLite by default — zero setup, matches the documented local-dev fallback.
    # Point this at a postgresql:// URL once Postgres is installed; no code changes needed.
    database_url: str = "sqlite:///./mentora.db"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7  # 7 days

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
