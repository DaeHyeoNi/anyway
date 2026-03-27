import hmac
import logging

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import RequireAdmin

logger = logging.getLogger(__name__)
from app.config import settings
from app.database import get_db
from app.photos.service import create_photo_from_upload, get_all_photos_admin, update_photo, delete_photo

router = APIRouter(prefix="/manage", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")
require_admin = RequireAdmin()


@router.get("/login")
async def login_page(request: Request):
    if request.session.get("is_admin"):
        return RedirectResponse("/manage", status_code=302)
    return templates.TemplateResponse(request, "admin/login.html", {"error": None})


@router.post("/login")
async def login(
    request: Request,
    admin_id: str = Form(...),
    password: str = Form(...),
):
    id_ok = hmac.compare_digest(admin_id, settings.admin_id)
    pw_ok = hmac.compare_digest(password, settings.admin_password)

    if id_ok and pw_ok:
        request.session["is_admin"] = True
        return RedirectResponse("/manage", status_code=302)

    return templates.TemplateResponse(
        request, "admin/login.html", {"error": "아이디 또는 비밀번호가 올바르지 않습니다."}, status_code=401
    )


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/manage/login", status_code=302)


@router.get("")
async def dashboard(request: Request, _=Depends(require_admin)):
    if isinstance(_, RedirectResponse):
        return _
    return templates.TemplateResponse(request, "admin/dashboard.html", {})


@router.get("/photos/upload")
async def upload_page(request: Request, _=Depends(require_admin)):
    if isinstance(_, RedirectResponse):
        return _
    return templates.TemplateResponse(request, "admin/upload.html", {"error": None, "success": None})


@router.post("/photos/exif")
async def read_exif(
    file: UploadFile = File(...),
    _=Depends(require_admin),
):
    """파일 선택 시 EXIF 파싱 결과 반환 (폼 자동 채우기용)"""
    if isinstance(_, RedirectResponse):
        return {}
    from pathlib import Path
    from app.ai.analyzer import extract_exif, reverse_geocode
    import tempfile, shutil

    suffix = Path(file.filename).suffix.lower() or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        exif = extract_exif(tmp_path)
        logger.info("EXIF parsed: %s", {k: v for k, v in exif.items() if k != "taken_at"})
        location = None
        if "latitude" in exif and "longitude" in exif:
            logger.info("GPS found: lat=%s, lon=%s — calling reverse_geocode", exif["latitude"], exif["longitude"])
            location = await reverse_geocode(exif["latitude"], exif["longitude"])
        else:
            logger.info("No GPS data in EXIF (keys: %s)", list(exif.keys()))
        return {
            "camera": exif.get("camera", ""),
            "taken_at": exif["taken_at"].strftime("%Y-%m-%d") if exif.get("taken_at") else "",
            "location": location or "",
        }
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/photos/upload")
async def upload_photo(
    request: Request,
    files: list[UploadFile] = File(...),
    title: str = Form(""),
    location: str = Form(""),
    camera: str = Form(""),
    taken_at: str = Form(""),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    if isinstance(_, RedirectResponse):
        return _

    meta_override = {
        "title": title.strip(),
        "location": location.strip(),
        "camera": camera.strip(),
        "taken_at": taken_at.strip(),
        "description": description.strip(),
    }

    errors = []
    count = 0
    for file in files:
        try:
            content = await file.read()
            await create_photo_from_upload(
                file_bytes=content,
                content_type=file.content_type,
                original_filename=file.filename,
                db=db,
                meta_override=meta_override,
            )
            count += 1
        except Exception as e:
            errors.append(f"{file.filename}: {e}")

    return templates.TemplateResponse(
        request,
        "admin/upload.html",
        {
            "success": f"{count}장 업로드 완료" if count else None,
            "error": "\n".join(errors) if errors else None,
        },
    )


@router.get("/photos")
async def photo_list(request: Request, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    if isinstance(_, RedirectResponse):
        return _
    photos = await get_all_photos_admin(db)
    return templates.TemplateResponse(request, "admin/photos.html", {"photos": photos})


@router.get("/photos/{photo_id}/edit")
async def edit_page(photo_id: int, request: Request, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
    if isinstance(_, RedirectResponse):
        return _
    from app.photos.service import get_photo
    photo = await get_photo(photo_id, db)
    if not photo:
        return RedirectResponse("/manage/photos", status_code=302)
    return templates.TemplateResponse(request, "admin/edit.html", {"photo": photo, "success": None, "error": None})


@router.post("/photos/{photo_id}/edit")
async def edit_photo(
    photo_id: int,
    request: Request,
    title: str = Form(""),
    description: str = Form(""),
    location: str = Form(""),
    camera: str = Form(""),
    lens: str = Form(""),
    aperture: str = Form(""),
    shutter_speed: str = Form(""),
    iso: str = Form(""),
    taken_at: str = Form(""),
    is_published: str = Form(""),
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if isinstance(_, RedirectResponse):
        return _
    data = {
        "title": title, "description": description, "location": location,
        "camera": camera, "lens": lens, "aperture": aperture,
        "shutter_speed": shutter_speed, "iso": iso,
        "taken_at": taken_at, "is_published": is_published,
    }
    photo = await update_photo(photo_id, data, db)
    from app.photos.service import get_photo
    return templates.TemplateResponse(
        request, "admin/edit.html",
        {"photo": photo, "success": "저장됐습니다." if photo else None, "error": None}
    )


@router.post("/photos/{photo_id}/delete")
async def delete_photo_route(
    photo_id: int,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if isinstance(_, RedirectResponse):
        return _
    await delete_photo(photo_id, db)
    return RedirectResponse("/manage/photos", status_code=302)
