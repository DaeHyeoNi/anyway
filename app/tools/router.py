from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/tools", tags=["tools"])
templates = Jinja2Templates(directory="app/templates")

TOOLS = [
    {
        "name": "Tick → DateTime",
        "description": "C# Ticks 값을 한국 시간(KST +9)으로 변환합니다.",
        "url": "/tools/calc",
    },
    {
        "name": "재미로 보는 운세",
        "description": "사주팔자, 이름궁합 등 동양 운세를 재미로 확인해보세요.",
        "url": "https://fortune.daehyeoni.dev",
    },
]


@router.get("/")
async def tools_index(request: Request):
    return templates.TemplateResponse(request, "tools/index.html", {"tools": TOOLS})


@router.get("/calc")
async def calc(request: Request):
    return templates.TemplateResponse(request, "tools/calc.html", {})

