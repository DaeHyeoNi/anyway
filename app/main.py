from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


from app.photos.router import router as photos_router  # noqa: E402
from app.admin.router import router as admin_router  # noqa: E402
from app.tools.router import router as tools_router  # noqa: E402

app.include_router(photos_router)
app.include_router(admin_router)
app.include_router(tools_router)


# 기존 GitHub Pages URL 호환성 유지
@app.get("/calc/")
async def calc_legacy_redirect():
    return RedirectResponse("/tools/calc", status_code=301)
