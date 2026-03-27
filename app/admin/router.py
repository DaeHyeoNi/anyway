import hmac

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import RequireAdmin
from app.config import settings
from app.database import get_db
from app.photos.service import create_photo_from_upload

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


@router.post("/photos/upload")
async def upload_photo(
    request: Request,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    if isinstance(_, RedirectResponse):
        return _

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
