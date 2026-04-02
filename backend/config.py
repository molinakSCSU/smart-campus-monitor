import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Smart Campus Object Monitor"
    DEBUG: bool = True

    # Database
    DATABASE_PATH: str = str(Path(__file__).parent / "campus_monitor.db")

    # GCP
    GOOGLE_CLOUD_PROJECT_ID: str = ""
    GOOGLE_CLOUD_STORAGE_BUCKET: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # CORS
    CORS_ORIGINS: str = "http://localhost:8501,http://localhost:3000"

    # Optional
    BIGQUERY_DATASET: str = "campus_monitor"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
