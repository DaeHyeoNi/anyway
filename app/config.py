import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings

_logger = logging.getLogger(__name__)


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
    r2_public_url: str = ""  # e.g. https://media.daehyeoni.dev

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _warn_insecure_defaults(self) -> "Settings":
        if self.secret_key == "change-me-in-production":
            _logger.warning("SECRET_KEY가 기본값입니다. 프로덕션에서는 반드시 변경하세요.")
        if not self.admin_password:
            _logger.warning("ADMIN_PASSWORD가 비어 있습니다. 어드민 로그인이 취약합니다.")
        return self


settings = Settings()
