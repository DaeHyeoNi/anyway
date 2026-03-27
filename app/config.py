from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "anyway"
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///./anyway.db"

    storage_path: str = "storage"
    thumb_size: tuple[int, int] = (800, 800)

    # Admin 인증
    admin_id: str = "admin"
    admin_password: str = ""
    secret_key: str = "change-me-in-production"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-preview"

    openai_api_key: str = ""

    # Cloudflare R2 (optional)
    r2_endpoint: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
