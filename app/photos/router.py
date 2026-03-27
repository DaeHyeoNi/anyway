from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.photos.service import get_all_countries, get_photo, get_photos_with_gps, get_published_photos

router = APIRouter(prefix="/photos", tags=["photos"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def photo_list(request: Request, country: str | None = None, db: AsyncSession = Depends(get_db)):
    photos = await get_published_photos(db, country=country)
    all_countries = await get_all_countries(db)

    # HTMX 요청이면 그리드만 반환
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request, "photos/_grid.html", {"photos": photos, "active_country": country}
        )

    return templates.TemplateResponse(
        request, "photos/index.html", {"photos": photos, "all_countries": all_countries, "active_country": country}
    )


@router.get("/map")
async def photo_map(request: Request, db: AsyncSession = Depends(get_db)):
    photos = await get_photos_with_gps(db)
    return templates.TemplateResponse(request, "photos/map.html", {"photos": photos})


@router.get("/{photo_id}/data")
async def photo_data(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await get_photo(photo_id, db)
    if not photo:
        raise HTTPException(status_code=404)
    return {
        "id": photo.id,
        "title": photo.title,
        "storage_url": photo.storage_url,
        "thumb_url": photo.thumb_url,
        "location": photo.location,
        "taken_at": photo.taken_at.strftime("%Y. %-m. %-d.") if photo.taken_at else None,
        "camera": photo.camera,
        "lens": photo.lens,
        "aperture": photo.aperture,
        "shutter_speed": photo.shutter_speed,
        "iso": photo.iso,
        "ai_tags": photo.ai_tags or [],
        "color_palette": photo.color_palette or [],
        "width": photo.width,
        "height": photo.height,
    }


@router.get("/{photo_id}")
async def photo_detail(photo_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    photo = await get_photo(photo_id, db)
    return templates.TemplateResponse(request, "photos/detail.html", {"photo": photo})
