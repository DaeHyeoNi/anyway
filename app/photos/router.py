from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.photos.service import get_all_tags, get_photo, get_photos_with_gps, get_published_photos

router = APIRouter(prefix="/photos", tags=["photos"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def photo_list(request: Request, tag: str | None = None, db: AsyncSession = Depends(get_db)):
    photos = await get_published_photos(db, tag=tag)
    all_tags = await get_all_tags(db)

    # HTMX 요청이면 그리드만 반환
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request, "photos/_grid.html", {"photos": photos, "active_tag": tag}
        )

    return templates.TemplateResponse(
        request, "photos/index.html", {"photos": photos, "all_tags": all_tags, "active_tag": tag}
    )


@router.get("/map")
async def photo_map(request: Request, db: AsyncSession = Depends(get_db)):
    photos = await get_photos_with_gps(db)
    return templates.TemplateResponse(request, "photos/map.html", {"photos": photos})


@router.get("/{photo_id}")
async def photo_detail(photo_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    photo = await get_photo(photo_id, db)
    return templates.TemplateResponse(request, "photos/detail.html", {"photo": photo})
