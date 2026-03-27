import hmac

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.deps import RequireAdmin
from app.config import settings

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
