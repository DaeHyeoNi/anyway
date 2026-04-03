"""EXIF 파싱 및 색상 팔레트 추출 테스트"""
from pathlib import Path

import piexif
import pytest
from PIL import Image

from app.ai.analyzer import extract_color_palette, extract_exif


def _make_jpeg(tmp_path: Path, exif_dict: dict | None = None) -> Path:
    """테스트용 JPEG 파일 생성"""
    img = Image.new("RGB", (100, 100), color=(128, 64, 32))
    path = tmp_path / "test.jpg"
    if exif_dict:
        exif_bytes = piexif.dump(exif_dict)
        img.save(path, format="JPEG", exif=exif_bytes)
    else:
        img.save(path, format="JPEG")
    return path


def _base_exif() -> dict:
    return {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}


# ── ZeroDivisionError 방어 ───────────────────────────────────────────────────

def test_extract_exif_zero_fnumber_denominator(tmp_path):
    """fnumber 분모 0 → aperture 키 없이 정상 반환 (ZeroDivisionError 없음)"""
    exif_dict = _base_exif()
    exif_dict["Exif"][piexif.ExifIFD.FNumber] = (28, 0)
    path = _make_jpeg(tmp_path, exif_dict)

    result = extract_exif(path)

    assert "aperture" not in result


def test_extract_exif_zero_focal_length_denominator(tmp_path):
    """focal_length 분모 0 → focal_length 키 없이 정상 반환"""
    exif_dict = _base_exif()
    exif_dict["Exif"][piexif.ExifIFD.FocalLength] = (50, 0)
    path = _make_jpeg(tmp_path, exif_dict)

    result = extract_exif(path)

    assert "focal_length" not in result


# ── 정상 파싱 ────────────────────────────────────────────────────────────────

def test_extract_exif_valid_aperture(tmp_path):
    """fnumber (28, 10) → aperture '2.8'"""
    exif_dict = _base_exif()
    exif_dict["Exif"][piexif.ExifIFD.FNumber] = (28, 10)
    path = _make_jpeg(tmp_path, exif_dict)

    result = extract_exif(path)

    assert result["aperture"] == "2.8"


def test_extract_exif_valid_focal_length(tmp_path):
    """focal_length (500, 10) → focal_length '50.0mm'"""
    exif_dict = _base_exif()
    exif_dict["Exif"][piexif.ExifIFD.FocalLength] = (500, 10)
    path = _make_jpeg(tmp_path, exif_dict)

    result = extract_exif(path)

    assert result["focal_length"] == "50.0mm"


def test_extract_exif_no_exif_returns_empty_dict(tmp_path):
    """EXIF 없는 파일 → 빈 dict (예외 없음)"""
    path = _make_jpeg(tmp_path)

    result = extract_exif(path)

    assert isinstance(result, dict)


def test_extract_exif_nonexistent_file():
    """존재하지 않는 파일 → 빈 dict (예외 없음)"""
    result = extract_exif(Path("/nonexistent/file.jpg"))

    assert result == {}


# ── 색상 팔레트 ──────────────────────────────────────────────────────────────

def test_extract_color_palette_returns_hex_colors(tmp_path):
    """색상 팔레트: HEX 형식 문자열 반환"""
    from PIL import ImageDraw

    img = Image.new("RGB", (150, 150))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 50, 149], fill=(255, 0, 0))
    draw.rectangle([50, 0, 100, 149], fill=(0, 255, 0))
    draw.rectangle([100, 0, 149, 149], fill=(0, 0, 255))
    path = tmp_path / "multi.jpg"
    img.save(path, format="JPEG")

    colors = extract_color_palette(path, n=3)

    assert len(colors) >= 1
    for color in colors:
        assert color.startswith("#")
        assert len(color) == 7


def test_extract_color_palette_nonexistent_file():
    """존재하지 않는 파일 → 빈 리스트 (예외 없음)"""
    result = extract_color_palette(Path("/nonexistent/file.jpg"))

    assert result == []
