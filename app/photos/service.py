import uuid
from pathlib import Path

from PIL import Image, ImageOps
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.ai.analyzer import extract_color_palette, extract_exif
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

    photo = Photo(
        filename=filename,
        storage_url=f"/storage/originals/{filename}",
        thumb_url=f"/storage/thumbnails/{filename}",
        width=width,
        height=height,
        file_size=len(file_bytes),
        color_palette=palette if palette else None,
        is_published=True,
        **exif,
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    return photo


async def get_published_photos(db: AsyncSession) -> list[Photo]:
    result = await db.execute(
        select(Photo).where(Photo.is_published == True).order_by(Photo.taken_at.desc().nullslast(), Photo.created_at.desc())
    )
    return result.scalars().all()


async def get_photo(photo_id: int, db: AsyncSession) -> Photo | None:
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    return result.scalar_one_or_none()
