"""GPS 파싱 & reverse geocoding 디버그 스크립트
사용법: uv run python debug_gps.py <이미지경로>
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def main(image_path: str):
    from app.ai.analyzer import extract_exif, reverse_geocode

    path = Path(image_path)
    print(f"파일: {path}")
    print("-" * 50)

    exif = extract_exif(path)
    print("EXIF 파싱 결과:")
    for k, v in exif.items():
        print(f"  {k}: {v}")

    print("-" * 50)
    if "latitude" in exif and "longitude" in exif:
        lat, lon = exif["latitude"], exif["longitude"]
        print(f"GPS: lat={lat}, lon={lon}")
        print("Nominatim 호출 중...")
        location = await reverse_geocode(lat, lon)
        print(f"위치: {location!r}")
    else:
        print("GPS 데이터 없음")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: uv run python debug_gps.py <이미지경로>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
