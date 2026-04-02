import asyncio
import io
import logging
import uuid
from pathlib import Path

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
register_heif_opener()
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.ai.analyzer import extract_color_palette, extract_exif, forward_geocode, reverse_geocode
from app.ai.tagger import generate_tags
from app.config import settings
from app.photos.models import Photo
from app.storage import delete_file, is_r2_enabled, upload_file

logger = logging.getLogger(__name__)


ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF", "MPO"}
THUMB_SIZE = (800, 800)


def _make_thumbnail(orig_path: Path, thumb_path: Path) -> tuple[bytes, int, int]:
    """동기 함수: 썸네일 생성 후 (thumb_bytes, width, height) 반환"""
    with Image.open(orig_path) as img:
        img = ImageOps.exif_transpose(img)
        width, height = img.size
        thumb_buf = io.BytesIO()
        thumb = img.copy()
        thumb.thumbnail(THUMB_SIZE, Image.LANCZOS)
        thumb.save(thumb_buf, format="JPEG", quality=85, optimize=True)
        thumb_bytes = thumb_buf.getvalue()
        thumb_path.write_bytes(thumb_bytes)
    return thumb_bytes, width, height


async def create_photo_from_upload(
    file_bytes: bytes,
    content_type: str,
    original_filename: str,
    db: AsyncSession,
    meta_override: dict | None = None,
) -> tuple[Photo, Path]:

    try:
        with Image.open(io.BytesIO(file_bytes)) as probe:
            if probe.format not in ALLOWED_FORMATS:
                raise ValueError(f"지원하지 않는 이미지 형식: {probe.format}")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"이미지를 열 수 없습니다: {original_filename} ({type(e).__name__}: {e})")

    ext = Path(original_filename).suffix.lower() or ".jpg"
    stem = uuid.uuid4().hex
    filename = f"{stem}{ext}"

    storage = Path(settings.storage_path)
    orig_path = storage / "originals" / filename
    thumb_path = storage / "thumbnails" / filename

    # 원본 저장 (로컬 — EXIF/썸네일 처리용)
    orig_path.parent.mkdir(parents=True, exist_ok=True)
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(orig_path.write_bytes, file_bytes)

    # 썸네일 생성
    thumb_bytes, width, height = await asyncio.to_thread(_make_thumbnail, orig_path, thumb_path)

    # EXIF 파싱
    exif = await asyncio.to_thread(extract_exif, orig_path)

    # 색상 팔레트
    palette = await asyncio.to_thread(extract_color_palette, orig_path)

    override = meta_override or {}

    # GPS → 지명 변환 (meta_override에 location 이미 있으면 스킵)
    location = None
    if not override.get("location") and "latitude" in exif and "longitude" in exif:
        location = await reverse_geocode(exif["latitude"], exif["longitude"])

    # R2 업로드 (설정된 경우) — 로컬 파일은 AI 태깅 후 백그라운드에서 삭제
    if is_r2_enabled():
        storage_url = await upload_file(f"originals/{filename}", file_bytes, content_type)
        thumb_url = await upload_file(f"thumbnails/{filename}", thumb_bytes, "image/jpeg")
    else:
        storage_url = f"/storage/originals/{filename}"
        thumb_url = f"/storage/thumbnails/{filename}"
    photo = Photo(
        filename=filename,
        storage_url=storage_url,
        thumb_url=thumb_url,
        width=width,
        height=height,
        file_size=len(file_bytes),
        color_palette=palette if palette else None,
        ai_tags=None,
        location=location or override.get("location") or None,
        title=override.get("title") or None,
        description=override.get("description") or None,
        is_published=True,
        **{k: v for k, v in exif.items() if v is not None},
    )
    # 수동 입력값이 있으면 EXIF보다 우선 적용
    if override.get("camera"):
        photo.camera = override["camera"]
    if override.get("taken_at"):
        from datetime import datetime
        try:
            photo.taken_at = datetime.strptime(override["taken_at"], "%Y-%m-%d")
        except ValueError:
            pass
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    return photo, orig_path


async def tag_and_cleanup(photo_id: int, orig_path: Path) -> None:
    """백그라운드: AI 태깅 후 R2 사용 시 로컬 파일 정리"""
    from app.database import AsyncSessionLocal
    try:
        tags = await generate_tags(orig_path)
        async with AsyncSessionLocal() as db:
            photo = await get_photo(photo_id, db)
            if photo:
                photo.ai_tags = tags or None
                await db.commit()
    except Exception as e:
        logger.error("AI 태깅 실패 (photo_id=%d): %s", photo_id, e)
    finally:
        if is_r2_enabled():
            storage = Path(settings.storage_path)
            (storage / "originals" / orig_path.name).unlink(missing_ok=True)
            (storage / "thumbnails" / orig_path.name).unlink(missing_ok=True)


async def get_published_photos(db: AsyncSession, country: str | None = None) -> list[Photo]:
    stmt = select(Photo).where(Photo.is_published == True)
    if country:
        safe_country = country.replace("%", r"\%").replace("_", r"\_")
        stmt = stmt.where(Photo.location.ilike(f"%{safe_country}", escape="\\"))
    stmt = stmt.order_by(Photo.taken_at.desc().nullslast(), Photo.id.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_all_countries(db: AsyncSession) -> list[str]:
    """location 마지막 쉼표 뒤 나라명 추출 (중복 제거, 알파벳순)"""
    result = await db.execute(
        select(Photo.location).where(Photo.is_published == True, Photo.location.is_not(None))
    )
    country_set = set()
    for (location,) in result:
        if location and "," in location:
            country = location.rsplit(",", 1)[-1].strip()
            if country:
                country_set.add(country)
    return sorted(country_set)


async def get_photos_with_gps(db: AsyncSession) -> list[Photo]:
    result = await db.execute(
        select(Photo).where(
            Photo.is_published == True,
            Photo.latitude.is_not(None),
            Photo.longitude.is_not(None),
        )
    )
    return result.scalars().all()


async def get_photo(photo_id: int, db: AsyncSession) -> Photo | None:
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    return result.scalar_one_or_none()


async def get_all_photos_admin(db: AsyncSession) -> list[Photo]:
    result = await db.execute(
        select(Photo).order_by(Photo.created_at.desc())
    )
    return result.scalars().all()


async def update_photo(photo_id: int, data: dict, db: AsyncSession) -> Photo | None:
    photo = await get_photo(photo_id, db)
    if not photo:
        return None
    from datetime import datetime
    prev_location = photo.location
    for field in ("title", "description", "location", "camera", "lens", "focal_length", "aperture", "shutter_speed"):
        val = data.get(field, "").strip()
        setattr(photo, field, val or None)

    # 좌표 직접 입력값 우선, 없으면 location forward geocoding
    def _to_float(v):
        try:
            return float(v.strip())
        except (ValueError, AttributeError):
            return None

    manual_lat = _to_float(data.get("latitude"))
    manual_lon = _to_float(data.get("longitude"))

    if manual_lat is not None and manual_lon is not None:
        photo.latitude, photo.longitude = manual_lat, manual_lon
    elif photo.location and photo.location != prev_location:
        coords = await forward_geocode(photo.location)
        if coords:
            photo.latitude, photo.longitude = coords
    elif not photo.location:
        photo.latitude = None
        photo.longitude = None
    iso = data.get("iso", "").strip()
    photo.iso = int(iso) if iso.isdigit() else None
    taken_at = data.get("taken_at", "").strip()
    if taken_at:
        try:
            photo.taken_at = datetime.strptime(taken_at, "%Y-%m-%d")
        except ValueError:
            pass
    else:
        photo.taken_at = None
    photo.is_published = data.get("is_published") == "on"
    tags_raw = data.get("ai_tags", "").strip()
    photo.ai_tags = [t.strip() for t in tags_raw.split(",") if t.strip()] or None
    await db.commit()
    await db.refresh(photo)
    return photo


async def delete_photo(photo_id: int, db: AsyncSession) -> bool:
    photo = await get_photo(photo_id, db)
    if not photo:
        return False
    if is_r2_enabled():
        await delete_file(f"originals/{photo.filename}")
        await delete_file(f"thumbnails/{photo.filename}")
    else:
        storage = Path(settings.storage_path)
        for path in (
            storage / "originals" / photo.filename,
            storage / "thumbnails" / photo.filename,
        ):
            path.unlink(missing_ok=True)
    await db.delete(photo)
    await db.commit()
    return True
