from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Detail Page Studio"
    database_url: str = "sqlite:///./backend/detail_page_studio.db"
    outputs_dir: str = "outputs"
    uploads_dir: str = "uploads"
    nanobanana_url: str = ""
    comfyui_url: str = "http://127.0.0.1:8188"
    default_image_provider: str = "mock"
    user_agent: str = "DetailPageStudioBot/1.0"
    scraper_timeout_s: int = 15

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()


def ensure_directories() -> None:
    Path(settings.outputs_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
