"""Configuration manager for IncuBrix PS4 Distribution Service."""
from pydantic import BaseModel, Field
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


class Settings(BaseModel):
    # Service
    HOST: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    PORT: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    ENV: str = Field(default_factory=lambda: os.getenv("ENV", "development"))
    LOG_LEVEL: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # Simulation & Safety
    SIMULATION_MODE: bool = Field(default_factory=lambda: os.getenv("SIMULATION_MODE", "true").lower() in ("true", "1", "yes"))
    MAX_RETRIES: int = Field(default_factory=lambda: int(os.getenv("MAX_RETRIES", "5")))
    REQUEST_TIMEOUT_SECONDS: float = Field(default_factory=lambda: float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10.0")))
    IDEMPOTENCY_TTL_SECONDS: int = Field(default_factory=lambda: int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "86400")))

    # Database Settings
    DATABASE_URL: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./incubrix_ps4.db"))

    # Storage Provider
    STORAGE_BACKEND: str = Field(default_factory=lambda: os.getenv("STORAGE_BACKEND", "local"))
    STORAGE_LOCAL_DIR: str = Field(default_factory=lambda: os.getenv("STORAGE_LOCAL_DIR", "./storage_data"))
    S3_ENDPOINT_URL: str = Field(default_factory=lambda: os.getenv("S3_ENDPOINT_URL", "http://localhost:9000"))
    S3_ACCESS_KEY: str = Field(default_factory=lambda: os.getenv("S3_ACCESS_KEY", "minioadmin"))
    S3_SECRET_KEY: str = Field(default_factory=lambda: os.getenv("S3_SECRET_KEY", "minioadmin"))
    S3_BUCKET_NAME: str = Field(default_factory=lambda: os.getenv("S3_BUCKET_NAME", "incubrix-artifacts"))
    S3_REGION: str = Field(default_factory=lambda: os.getenv("S3_REGION", "us-east-1"))

    # External AI Provider
    AI_PROVIDER: str = Field(default_factory=lambda: os.getenv("AI_PROVIDER", "mock"))
    AI_API_KEY: str = Field(default_factory=lambda: os.getenv("AI_API_KEY", "mock-key-for-local-test"))
    AI_MODEL_NAME: str = Field(default_factory=lambda: os.getenv("AI_MODEL_NAME", "mock-rules-engine-v1"))

    # Webhook & Signing
    WEBHOOK_HMAC_SECRET: str = Field(default_factory=lambda: os.getenv("WEBHOOK_HMAC_SECRET", "incubrix-dev-secret-key-32chars-min"))

    # Recertification Policy
    RECERTIFICATION_INTERVAL_DAYS: int = Field(default_factory=lambda: int(os.getenv("RECERTIFICATION_INTERVAL_DAYS", "30")))

    # Mock Server
    MOCK_SERVER_PORT: int = Field(default_factory=lambda: int(os.getenv("MOCK_SERVER_PORT", "8080")))
    MOCK_SERVER_HOST: str = Field(default_factory=lambda: os.getenv("MOCK_SERVER_HOST", "http://localhost:8080"))


settings = Settings()
