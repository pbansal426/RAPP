from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# pydantic-settings parses .env into the Settings object below, but doesn't
# populate os.environ for other consumers. genai.Client() is meant to pick up
# GEMINI_API_KEY from the environment automatically (per google-genai's own
# convention), so we load .env into the process environment explicitly.
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "rapp-backend"
    debug: bool = False
    port: int = 8000
    host: str = "127.0.0.1"

    # API endpoints and URLs
    nhtsa_base_url: str = "https://vpic.nhtsa.dot.gov/api/vehicles"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    # Keys / Secrets (Stubbed / optional)
    gemini_api_key: str | None = None
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_single: str = "price_xxx"
    stripe_price_vin_pass: str = "price_xxx"

    # RAG settings
    vector_store: str = "chromadb"
    chroma_db_path: str = "./data/chroma_db"

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:3099"

    # Logging
    log_format: str = "dev"

    # Database & Authentication (SQLite for local dev; point at a Postgres
    # URL in production). jwt_secret_key's default is local-dev only --
    # always set a real secret via the environment in any deployed environment.
    database_url: str | None = None
    jwt_secret_key: str = "supersecretkeyforlocaldev"


settings = Settings()
