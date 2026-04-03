"""photos/service.py 핵심 로직 테스트"""
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.photos.service import _make_thumbnail


# ── _make_thumbnail ──────────────────────────────────────────────────────────

def test_make_thumbnail_creates_file(tmp_path):
    """썸네일 파일 생성 + (thumb_bytes, width, height) 반환"""
    orig = tmp_path / "orig.jpg"
    thumb = tmp_path / "thumb.jpg"
    Image.new("RGB", (2000, 1000), color=(0, 128, 255)).save(orig)

    thumb_bytes, width, height = _make_thumbnail(orig, thumb)

    assert thumb.exists()
    assert len(thumb_bytes) > 0
    assert width == 2000
    assert height == 1000
    assert thumb.stat().st_size == len(thumb_bytes)


def test_make_thumbnail_respects_size_limit(tmp_path):
    """800x800 제한 내로 썸네일 축소"""
    orig = tmp_path / "orig.jpg"
    thumb = tmp_path / "thumb.jpg"
    Image.new("RGB", (3000, 2000)).save(orig)

    _make_thumbnail(orig, thumb)

    with Image.open(thumb) as t:
        assert t.width <= 800
        assert t.height <= 800


# ── tag_and_cleanup ──────────────────────────────────────────────────────────

async def test_tag_and_cleanup_logs_error_on_failure(tmp_path, caplog):
    """AI 태깅 실패 시 에러 로깅, 예외 전파 안 함"""
    orig = tmp_path / "originals" / "test.jpg"
    orig.parent.mkdir(parents=True)
    orig.write_bytes(b"fake-image-data")

    with patch("app.photos.service.generate_tags", side_effect=Exception("Gemini down")):
        with patch("app.photos.service.is_r2_enabled", return_value=False):
            with caplog.at_level(logging.ERROR, logger="app.photos.service"):
                from app.photos.service import tag_and_cleanup

                await tag_and_cleanup(photo_id=999, orig_path=orig)

    assert "AI 태깅 실패" in caplog.text
    assert "999" in caplog.text


async def test_tag_and_cleanup_cleans_local_files_on_failure(tmp_path):
    """AI 태깅 실패해도 R2 사용 시 로컬 파일 삭제"""
    orig = tmp_path / "originals" / "test.jpg"
    thumb = tmp_path / "thumbnails" / "test.jpg"
    orig.parent.mkdir(parents=True)
    thumb.parent.mkdir(parents=True)
    orig.write_bytes(b"fake")
    thumb.write_bytes(b"fake")

    with patch("app.photos.service.generate_tags", side_effect=Exception("fail")):
        with patch("app.photos.service.is_r2_enabled", return_value=True):
            with patch("app.photos.service.settings") as mock_settings:
                mock_settings.storage_path = str(tmp_path)
                from app.photos.service import tag_and_cleanup

                await tag_and_cleanup(photo_id=1, orig_path=orig)

    assert not orig.exists()
    assert not thumb.exists()


# ── get_published_photos (country 필터) ──────────────────────────────────────

async def test_get_published_photos_wildcard_escaped():
    """country 파라미터의 % 문자가 이스케이프되어 SQL에 전달됨"""
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    from app.photos.service import get_published_photos

    # % 와일드카드 포함 country — 예외 없이 실행되어야 함
    result = await get_published_photos(mock_db, country="%")

    assert result == []
    mock_db.execute.assert_called_once()

    # 실제 SQL 문자열에서 이스케이프 확인
    stmt = mock_db.execute.call_args[0][0]
    compiled = stmt.compile(compile_kwargs={"literal_binds": True})
    assert r"\%" in str(compiled)


# ── 스토리지 디렉토리 자동 생성 ──────────────────────────────────────────────

async def test_create_photo_creates_storage_dirs(tmp_path):
    """originals / thumbnails 디렉토리가 없어도 자동 생성"""
    storage = tmp_path / "new_storage"  # 존재하지 않는 경로

    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    import io

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    file_bytes = buf.getvalue()

    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("app.photos.service.settings") as mock_settings:
        mock_settings.storage_path = str(storage)
        with patch("app.photos.service.is_r2_enabled", return_value=False):
            with patch("app.photos.service.extract_exif", return_value={}):
                with patch("app.photos.service.extract_color_palette", return_value=[]):
                    with patch("app.photos.service.reverse_geocode", return_value=None):
                        from app.photos.service import create_photo_from_upload

                        await create_photo_from_upload(
                            file_bytes=file_bytes,
                            content_type="image/jpeg",
                            original_filename="test.jpg",
                            db=mock_db,
                        )

    assert (storage / "originals").exists()
    assert (storage / "thumbnails").exists()
