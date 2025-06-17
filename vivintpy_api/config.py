from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    APP_NAME: str = "VivintPy API"
    DEBUG_MODE: bool = False
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7)) # API Refresh token expiry in days
    VIVINT_USERNAME: str | None = None
    VIVINT_PASSWORD: str | None = None
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST")
    REDIS_PORT: int = os.getenv("REDIS_PORT")
    REDIS_DB: int = os.getenv("REDIS_DB")
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
