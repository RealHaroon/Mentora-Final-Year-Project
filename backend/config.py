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

    # Phase 6 — Model Manager. Paths are relative to backend/'s own cwd
    # (where uvicorn is started from), matching ml_models/saved/'s location
    # as a sibling of backend/.
    debug: bool = False
    model1_path: str = "../ml_models/saved/model1_gap_classifier"
    model2_path: str = "../ml_models/saved/model2_question_generator"
    model3_path: str = "../ml_models/saved/model3_trajectory_predictor/lstm_final.pt"
    model4_path: str = "../ml_models/saved/model4_career_matcher"
    model5_path: str = "../ml_models/saved/model5_cv_ner"
    topics_json: str = "./data/topics.json"
    m5_id2tag_json: str = "./data/m5_id2tag.json"


settings = Settings()
