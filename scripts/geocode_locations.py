"""location 텍스트 → 위경도 일괄 변환
사용법: uv run python scripts/geocode_locations.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.ai.analyzer import forward_geocode
from app.config import settings
from app.photos.models import Photo


async def main():
    engine = create_async_engine(settings.database_url)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        result = await db.execute(
            select(Photo).where(
                Photo.location.is_not(None),
                Photo.latitude.is_(None),
            )
        )
        photos = result.scalars().all()

    print(f"좌표 없는 사진: {len(photos)}장")

    ok = fail = 0
    async with Session() as db:
        for photo in photos:
            coords = await forward_geocode(photo.location)
            if coords:
                photo.latitude, photo.longitude = coords
                db.add(photo)
                print(f"  [OK] {photo.location!r} → {coords}")
                ok += 1
            else:
                print(f"  [FAIL] {photo.location!r}")
                fail += 1
            await asyncio.sleep(1)  # Nominatim rate limit

        await db.commit()

    print(f"\n완료 — 성공: {ok}, 실패: {fail}")


if __name__ == "__main__":
    asyncio.run(main())
