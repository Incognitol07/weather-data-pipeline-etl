# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Weather Data Pipeline"
    APP_DESCRIPTION: str = "An ETL weather data pipeline"
    ENVIRONMENT: str = "development"
    DEBUG: bool = ENVIRONMENT == "development"

    # Database URL (via .env)
    DATABASE_URL: str

    # JWT and authentication settings
    JWT_SECRET_KEY: str

    # OpenWeather API key (via .env)
    WEATHER_API_KEY: str

    # Scheduler intervals & retention
    CURRENT_WEATHER_INTERVAL_HOURS: int = 1
    FORECAST_INTERVAL_HOURS: int = 3

    # CORS & hosts
    ALLOWED_HOSTS: list[str] = ["*"]
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
