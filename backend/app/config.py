# Environment and configuration helpers for AllerSense backend
from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "AllerSense"
    debug: bool = True

settings = Settings()
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://medguard:medguard_secret@postgres:5432/medguard"
    DATABASE_URL_SYNC: str = "postgresql://medguard:medguard_secret@postgres:5432/medguard"

    # Redis / Valkey
    REDIS_URL: str = "redis://valkey:6379/0"

    # AI Backend: "ollama", "huggingface_local", "huggingface_api"
    AI_BACKEND: str = "ollama"

    # Ollama settings
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "medgemma:4b"

    # HuggingFace settings (local transformers or Inference API)
    HF_MODEL_ID: str = "google/medgemma-4b-it"
    HF_TOKEN: str = ""  # Required for gated models like MedGemma
    HF_DEVICE: str = "auto"  # auto, cpu, cuda, mps
    HF_TORCH_DTYPE: str = "auto"  # auto, float16, bfloat16, float32
    HF_MAX_NEW_TOKENS: int = 1024

    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET: str = "prescriptions"
    MINIO_USE_SSL: bool = False

    # Keycloak
    KEYCLOAK_URL: str = "http://keycloak:8080"
    KEYCLOAK_REALM: str = "medguard"
    KEYCLOAK_CLIENT_ID: str = "medguard-api"
    KEYCLOAK_PUBLIC_KEY: str = ""

    # App
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "change-me-in-production"
    APP_DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    # OpenFDA
    OPENFDA_API_URL: str = "https://api.fda.gov/drug"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()