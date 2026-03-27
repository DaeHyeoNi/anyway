"""로컬 스토리지 사진 → R2 마이그레이션
사용법: uv run python scripts/migrate_to_r2.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.photos.models import Photo
from app.storage import delete_file, is_r2_enabled, upload_file


async def migrate():
    if not is_r2_enabled():
        print("R2 설정이 없습니다. .env를 확인하세요.")
        sys.exit(1)

    engine = create_async_engine(settings.database_url)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    storage = Path(settings.storage_path)

    async with Session() as db:
        result = await db.execute(select(Photo))
        photos = result.scalars().all()

    print(f"총 {len(photos)}장 확인")

    ok, skip, fail = 0, 0, 0

    async with Session() as db:
        for photo in photos:
            # 이미 R2 URL이면 스킵
            if photo.storage_url and not photo.storage_url.startswith("/storage"):
                print(f"  [SKIP] {photo.filename} — 이미 R2")
                skip += 1
                continue

            orig_path = storage / "originals" / photo.filename
            thumb_path = storage / "thumbnails" / photo.filename

            if not orig_path.exists():
                print(f"  [SKIP] {photo.filename} — 로컬 파일 없음")
                skip += 1
                continue

            try:
                orig_bytes = orig_path.read_bytes()
                new_storage_url = await upload_file(
                    f"originals/{photo.filename}", orig_bytes, "image/jpeg"
                )

                if thumb_path.exists():
                    thumb_bytes = thumb_path.read_bytes()
                    new_thumb_url = await upload_file(
                        f"thumbnails/{photo.filename}", thumb_bytes, "image/jpeg"
                    )
                else:
                    new_thumb_url = new_storage_url

                photo.storage_url = new_storage_url
                photo.thumb_url = new_thumb_url
                db.add(photo)

                print(f"  [OK] {photo.filename}")
                ok += 1

            except Exception as e:
                print(f"  [FAIL] {photo.filename}: {e}")
                fail += 1

        await db.commit()

    print(f"\n완료 — 성공: {ok}, 스킵: {skip}, 실패: {fail}")

    if ok > 0:
        print("\n로컬 파일 삭제하려면 아래 명령 실행:")
        print("  rm -rf storage/originals/* storage/thumbnails/*")


if __name__ == "__main__":
    asyncio.run(migrate())
