import uuid
from pathlib import Path

from PIL import Image, ImageOps
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.ai.analyzer import extract_color_palette, extract_exif, reverse_geocode
from app.ai.tagger import generate_tags
from app.config import settings
from app.photos.models import Photo


ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
THUMB_SIZE = (800, 800)


async def create_photo_from_upload(
    file_bytes: bytes,
    content_type: str,
    original_filename: str,
    db: AsyncSession,
) -> Photo:
    if content_type not in ALLOWED_TYPES:
        raise ValueError(f"지원하지 않는 파일 형식: {content_type}")

    ext = Path(original_filename).suffix.lower() or ".jpg"
    stem = uuid.uuid4().hex
    filename = f"{stem}{ext}"

    storage = Path(settings.storage_path)
    orig_path = storage / "originals" / filename
    thumb_path = storage / "thumbnails" / filename

    # 원본 저장
    orig_path.write_bytes(file_bytes)

    # 썸네일 생성
    with Image.open(orig_path) as img:
        img = ImageOps.exif_transpose(img)  # EXIF 회전 보정
        width, height = img.size
        thumb = img.copy()
        thumb.thumbnail(THUMB_SIZE, Image.LANCZOS)
        thumb.save(thumb_path, quality=85, optimize=True)

    # EXIF 파싱
    exif = extract_exif(orig_path)

    # 색상 팔레트
    palette = extract_color_palette(orig_path)

    # GPS → 지명 변환
    location = None
    if "latitude" in exif and "longitude" in exif:
        location = await reverse_geocode(exif["latitude"], exif["longitude"])

    # AI 태깅 (API 키 없으면 스킵)
    tags = await generate_tags(orig_path)

    photo = Photo(
        filename=filename,
        storage_url=f"/storage/originals/{filename}",
        thumb_url=f"/storage/thumbnails/{filename}",
        width=width,
        height=height,
        file_size=len(file_bytes),
        color_palette=palette if palette else None,
        ai_tags=tags if tags else None,
        location=location,
        is_published=True,
        **exif,
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    return photo


async def get_published_photos(db: AsyncSession, tag: str | None = None) -> list[Photo]:
    stmt = select(Photo).where(Photo.is_published == True)
    if tag:
        stmt = stmt.where(Photo.ai_tags.contains([tag]))
    stmt = stmt.order_by(Photo.taken_at.desc().nullslast(), Photo.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_all_tags(db: AsyncSession) -> list[str]:
    """전체 사진에서 태그 목록 수집 (중복 제거, 알파벳순)"""
    result = await db.execute(
        select(Photo.ai_tags).where(Photo.is_published == True, Photo.ai_tags.is_not(None))
    )
    tag_set = set()
    for (tags,) in result:
        if isinstance(tags, list):
            tag_set.update(tags)
    return sorted(tag_set)


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
