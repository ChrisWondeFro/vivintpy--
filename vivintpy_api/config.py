from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "VivintPy API"
    DEBUG_MODE: bool = False
    JWT_SECRET_KEY: str = "your-secret-key"  # Change this in production!
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    VIVINT_USERNAME: str | None = None
    VIVINT_PASSWORD: str | None = None
    ALLOWED_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
