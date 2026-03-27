from datetime import datetime
from fractions import Fraction
from pathlib import Path

import piexif
from PIL import Image


def extract_exif(image_path: Path) -> dict:
    result = {}
    try:
        exif_bytes = piexif.load(str(image_path))
    except Exception:
        return result

    ifd = exif_bytes.get("Exif", {})
    ifd0 = exif_bytes.get("0th", {})
    gps = exif_bytes.get("GPS", {})

    # 촬영일
    date_raw = ifd.get(piexif.ExifIFD.DateTimeOriginal)
    if date_raw:
        try:
            result["taken_at"] = datetime.strptime(date_raw.decode(), "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass

    # 카메라 / 렌즈
    make = ifd0.get(piexif.ImageIFD.Make, b"").decode(errors="ignore").strip("\x00").strip()
    model = ifd0.get(piexif.ImageIFD.Model, b"").decode(errors="ignore").strip("\x00").strip()
    if make or model:
        result["camera"] = f"{make} {model}".strip()

    lens_raw = ifd.get(piexif.ExifIFD.LensModel)
    if lens_raw:
        result["lens"] = lens_raw.decode(errors="ignore").strip("\x00").strip()

    # 조리개
    fnumber = ifd.get(piexif.ExifIFD.FNumber)
    if fnumber:
        result["aperture"] = str(round(fnumber[0] / fnumber[1], 1))

    # 셔터스피드
    exposure = ifd.get(piexif.ExifIFD.ExposureTime)
    if exposure:
        frac = Fraction(exposure[0], exposure[1]).limit_denominator(10000)
        result["shutter_speed"] = str(frac)

    # ISO
    iso = ifd.get(piexif.ExifIFD.ISOSpeedRatings)
    if iso:
        result["iso"] = iso

    # GPS
    if gps:
        lat = _dms_to_decimal(gps.get(piexif.GPSIFD.GPSLatitude), gps.get(piexif.GPSIFD.GPSLatitudeRef))
        lon = _dms_to_decimal(gps.get(piexif.GPSIFD.GPSLongitude), gps.get(piexif.GPSIFD.GPSLongitudeRef))
        if lat and lon:
            result["latitude"] = lat
            result["longitude"] = lon

    return result


def _dms_to_decimal(dms, ref) -> float | None:
    if not dms or not ref:
        return None
    try:
        d = dms[0][0] / dms[0][1]
        m = dms[1][0] / dms[1][1]
        s = dms[2][0] / dms[2][1]
        decimal = d + m / 60 + s / 3600
        if ref in (b"S", b"W"):
            decimal *= -1
        return round(decimal, 6)
    except Exception:
        return None


def extract_color_palette(image_path: Path, n: int = 5) -> list[str]:
    """대표 색상 n개를 HEX 문자열로 반환"""
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB").resize((150, 150))
            result = img.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
            palette_rgb = result.getpalette()[:n * 3]
            colors = []
            for i in range(0, len(palette_rgb), 3):
                r, g, b = palette_rgb[i], palette_rgb[i + 1], palette_rgb[i + 2]
                colors.append(f"#{r:02x}{g:02x}{b:02x}")
            return colors
    except Exception:
        return []
