import asyncio
import os
from pathlib import Path

# 앱 모듈이 임포트되기 전에 테스트 환경변수 설정
_TEST_DB = Path(__file__).parent / "test.db"
_TEST_STORAGE = Path(__file__).parent / "test_storage"

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ADMIN_ID"] = "testadmin"
os.environ["ADMIN_PASSWORD"] = "testpass"
os.environ["STORAGE_PATH"] = str(_TEST_STORAGE)
os.environ["GEMINI_API_KEY"] = ""
os.environ["R2_ENDPOINT"] = ""
os.environ["R2_ACCESS_KEY"] = ""
os.environ["R2_SECRET_KEY"] = ""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


def pytest_configure(config):
    """세션 시작 전 테스트 DB 테이블 생성"""
    _TEST_STORAGE.mkdir(parents=True, exist_ok=True)
    (_TEST_STORAGE / "originals").mkdir(exist_ok=True)
    (_TEST_STORAGE / "thumbnails").mkdir(exist_ok=True)

    async def _create():
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.photos.models import Base

        engine = create_async_engine(f"sqlite+aiosqlite:///{_TEST_DB}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create())


def pytest_unconfigure(config):
    """세션 종료 후 테스트 DB 및 스토리지 정리"""
    import shutil

    _TEST_DB.unlink(missing_ok=True)
    if _TEST_STORAGE.exists():
        shutil.rmtree(_TEST_STORAGE, ignore_errors=True)


@pytest_asyncio.fixture
async def client():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
