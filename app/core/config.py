# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Weather Data Pipeline"
    APP_DESCRIPTION: str = "An ETL weather data pipeline"
    ENVIRONMENT: str = "development"
    DEBUG: bool = ENVIRONMENT == "development"

    # This one really should come from env for security!
    DATABASE_URL: str

    # JWT and authentication settings
    JWT_SECRET_KEY: str

    # For simple APIs you might default to a single key,
    # but still allow override in production.
    WEATHER_API_KEY: str

    # Other security settings
    ALLOWED_HOSTS: list[str] = ["*"]
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    class Config:
        # Automatically read from a .env file in your project root
        env_file = ".env"
        env_file_encoding = "utf-8"

# Instantiate settings
settings = Settings()
