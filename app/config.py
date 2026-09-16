from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    APP_NAME: str = "AI TAM SAM SOM Market Analyzer"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Ollama LLM Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:8b"
    OLLAMA_TIMEOUT_SECONDS: float = 180.0

    # Source Fetching Configuration
    SOURCE_FETCH_TIMEOUT_SECONDS: float = 15.0
    SOURCE_FETCH_MAX_BYTES: int = 5_242_880  # 5 MB
    SOURCE_FETCH_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "TAM-SAM-SOM-Analyzer/0.1.0 (Evidence Research Bot)"
    )

    # Search Discovery Provider Configuration
    SEARCH_PROVIDER: str = "mock"  # "mock", "live", "tavily", "searxng", "custom"
    SEARCH_API_URL: str | None = None
    SEARCH_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None
    SEARCH_TIMEOUT_SECONDS: float = 15.0

    # Persistence Configuration
    DATABASE_PATH: str = "data/market_analyses.db"

    # CORS Configuration
    CORS_ALLOW_ORIGINS: str = "*"

    # Server & Logging Configuration
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
