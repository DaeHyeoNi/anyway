from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/tools", tags=["tools"])
templates = Jinja2Templates(directory="app/templates")

TOOLS = [
    {
        "name": "Tick → DateTime",
        "description": "C# Ticks 값을 한국 시간(KST +9)으로 변환합니다.",
        "url": "/tools/calc",
    },
]


@router.get("/")
async def tools_index(request: Request):
    return templates.TemplateResponse(request, "tools/index.html", {"tools": TOOLS})


@router.get("/calc")
async def calc(request: Request):
    return templates.TemplateResponse(request, "tools/calc.html", {})
