from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)

    # EXIF
    taken_at: Mapped[datetime | None] = mapped_column(DateTime)
    location: Mapped[str | None] = mapped_column(String)  # GPS → 지명
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    camera: Mapped[str | None] = mapped_column(String)
    lens: Mapped[str | None] = mapped_column(String)
    aperture: Mapped[str | None] = mapped_column(String)
    shutter_speed: Mapped[str | None] = mapped_column(String)
    iso: Mapped[int | None] = mapped_column(Integer)

    # 파일 정보
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    file_size: Mapped[int | None] = mapped_column(Integer)
    storage_url: Mapped[str] = mapped_column(String, nullable=False)
    thumb_url: Mapped[str | None] = mapped_column(String)

    # AI
    ai_tags: Mapped[list | None] = mapped_column(JSON)
    color_palette: Mapped[list | None] = mapped_column(JSON)

    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    album_photos: Mapped[list["AlbumPhoto"]] = relationship(back_populates="photo")


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    cover_photo_id: Mapped[int | None] = mapped_column(ForeignKey("photos.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    album_photos: Mapped[list["AlbumPhoto"]] = relationship(back_populates="album")


class AlbumPhoto(Base):
    __tablename__ = "album_photos"

    album_id: Mapped[int] = mapped_column(ForeignKey("albums.id"), primary_key=True)
    photo_id: Mapped[int] = mapped_column(ForeignKey("photos.id"), primary_key=True)
    order: Mapped[int] = mapped_column(Integer, default=0)

    album: Mapped["Album"] = relationship(back_populates="album_photos")
    photo: Mapped["Photo"] = relationship(back_populates="album_photos")
