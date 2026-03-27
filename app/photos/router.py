from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.photos.service import get_photo, get_published_photos

router = APIRouter(prefix="/photos", tags=["photos"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def photo_list(request: Request, db: AsyncSession = Depends(get_db)):
    photos = await get_published_photos(db)
    return templates.TemplateResponse(request, "photos/index.html", {"photos": photos})


@router.get("/{photo_id}")
async def photo_detail(photo_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    photo = await get_photo(photo_id, db)
    return templates.TemplateResponse(request, "photos/detail.html", {"photo": photo})
