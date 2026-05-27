import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import RequireAdmin

logger = logging.getLogger(__name__)
from app.config import settings
from app.database import get_db
from app.photos.service import create_photo_from_upload, get_all_photos_admin, update_photo, delete_photo, process_photo_pipeline

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


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/manage/login", status_code=302)


@router.get("")
async def dashboard(request: Request, _=Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/dashboard.html", {})


@router.get("/photos/upload")
async def upload_page(request: Request, _=Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/upload.html", {"error": None, "success": None})


@router.post("/photos/exif")
async def read_exif(
    file: UploadFile = File(...),
    _=Depends(require_admin),
):
    """파일 선택 시 EXIF 파싱 결과 반환 (폼 자동 채우기용)"""
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
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    title: str = Form(""),
    location: str = Form(""),
    camera: str = Form(""),
    taken_at: str = Form(""),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
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
            await file.seek(0)
            content = await file.read()
            logger.warning("upload: %s size=%d content_type=%s", file.filename, len(content), file.content_type)
            if not content:
                errors.append(f"{file.filename}: 파일이 비어있습니다 (0 bytes)")
                continue
            photo, orig_path = await create_photo_from_upload(
                file_bytes=content,
                content_type=file.content_type,
                original_filename=file.filename,
                db=db,
                meta_override=meta_override,
            )
            background_tasks.add_task(process_photo_pipeline, photo.id, orig_path, content, file.content_type)
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
    photos = await get_all_photos_admin(db)
    return templates.TemplateResponse(request, "admin/photos.html", {"photos": photos})


@router.get("/photos/{photo_id}/edit")
async def edit_page(photo_id: int, request: Request, _=Depends(require_admin), db: AsyncSession = Depends(get_db)):
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
    focal_length: str = Form(""),
    aperture: str = Form(""),
    shutter_speed: str = Form(""),
    iso: str = Form(""),
    taken_at: str = Form(""),
    is_published: str = Form(""),
    ai_tags: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form(""),
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = {
        "title": title, "description": description, "location": location,
        "camera": camera, "lens": lens, "focal_length": focal_length, "aperture": aperture,
        "shutter_speed": shutter_speed, "iso": iso,
        "taken_at": taken_at, "is_published": is_published,
        "ai_tags": ai_tags,
        "latitude": latitude, "longitude": longitude,
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
    await delete_photo(photo_id, db)
    return RedirectResponse("/manage/photos", status_code=302)


@router.post("/photos/{photo_id}/regenerate-tags")
async def regenerate_photo_tags(
    photo_id: int,
    request: Request,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from pathlib import Path
    import tempfile
    import httpx
    from app.photos.service import get_photo
    from app.ai.tagger import generate_tags

    logger.info("[REGENERATE TAGS] 시작 - photo_id: %d", photo_id)

    photo = await get_photo(photo_id, db)
    if not photo:
        logger.warning("[REGENERATE TAGS] 실패 - DB에 존재하지 않는 사진입니다. photo_id: %d", photo_id)
        return RedirectResponse("/manage/photos", status_code=302)

    # 1. 파일 경로 확인 및 이미지 분석 준비
    storage_path = Path(settings.storage_path)
    local_orig_path = storage_path / "originals" / photo.filename

    tmp_path = None
    tags = []

    try:
        if local_orig_path.exists():
            logger.info("[REGENERATE TAGS] 로컬 원본 파일 발견. 경로: %s", local_orig_path)
            tags = await generate_tags(local_orig_path)
        else:
            # R2 등 리모트 스토리지 사용 중으로 인해 로컬 파일이 없는 경우,
            # photo.storage_url로부터 이미지를 임시 Fetch하여 분석합니다.
            url = photo.storage_url
            logger.info("[REGENERATE TAGS] 로컬 파일 없음 -> 리모트 스토리지 URL에서 Fetch 시도: %s", url)
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                image_bytes = resp.content

            with tempfile.NamedTemporaryFile(suffix=Path(photo.filename).suffix, delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = Path(tmp.name)

            logger.info("[REGENERATE TAGS] 리모트 이미지 Fetch 성공. 크기: %d bytes. 임시 경로: %s", len(image_bytes), tmp_path)
            tags = await generate_tags(tmp_path)

        if tags:
            photo.ai_tags = tags
            await db.commit()
            await db.refresh(photo)
            logger.info("[REGENERATE TAGS] 성공 - 태그가 데이터베이스에 반영되었습니다. photo_id: %d, 태그: %r", photo_id, tags)
            success_msg = "AI 태그가 성공적으로 재생성되었습니다."
            error_msg = None
        else:
            logger.warning("[REGENERATE TAGS] AI 분석 완료되었으나 태그가 빈 값으로 반환되었습니다. photo_id: %d", photo_id)
            success_msg = None
            error_msg = "Gemini AI 태그 재생성에 실패했습니다. API 키 및 모델 설정을 확인하세요."

    except Exception as e:
        logger.error("[REGENERATE TAGS] 예외 에러 발생 - photo_id: %d, 에러: %s", photo_id, e, exc_info=True)
        success_msg = None
        error_msg = f"태그 재생성 중 에러가 발생했습니다: {e}"
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink(missing_ok=True)
                logger.info("[REGENERATE TAGS] 임시 격리 이미지 파일 삭제 완료. 경로: %s", tmp_path)
            except Exception as clean_err:
                logger.warning("[REGENERATE TAGS] 임시 이미지 정리 오류: %s", clean_err)

    return templates.TemplateResponse(
        request,
        "admin/edit.html",
        {"photo": photo, "success": success_msg, "error": error_msg},
    )
