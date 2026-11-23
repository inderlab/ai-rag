from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    APP_NAME: str = "VidMind AI"
    ENV: str = "dev"
    CORS_ORIGINS: str = "http://localhost:5173"

    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-haiku-5-5"
    CLAUDE_EFFORT: str = "low"

    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-small"
    EMBEDDING_BATCH_SIZE: int = 32

    CHUNK_MAX_WORDS: int = 300
    CHUNK_OVERLAP_WORDS: int = 50

    CHROMA_DIR: str = str(BACKEND_DIR / "data" / "chroma")
    CHROMA_COLLECTION: str = "vidmind_chunks"
    SEARCH_K: int = 6

    AUTO_INSIGHTS: bool = True
    INSIGHTS_MAX_WORDS: int = 40000

    AUTH_REQUIRED: bool = False
    JWT_SECRET: str = ""
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7

    UPLOAD_DIR: str = str(BACKEND_DIR / "data" / "uploads")
    UPLOAD_MAX_MB: int = 500
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"
    FFMPEG_BIN: str = "ffmpeg"

    N8N_WEBHOOK_URL: str = ""
    PUBLIC_APP_URL: str = "http://localhost:5173"

    DATABASE_URL: str = f"sqlite:///{BACKEND_DIR / 'data' / 'vidmind.db'}"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
