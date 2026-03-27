import asyncio
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from app.config import settings


def is_r2_enabled() -> bool:
    return bool(settings.r2_endpoint and settings.r2_access_key and settings.r2_secret_key and settings.r2_bucket)


@lru_cache(maxsize=1)
def _get_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key,
        aws_secret_access_key=settings.r2_secret_key,
        region_name="auto",
    )


def _upload_sync(key: str, data: bytes, content_type: str) -> None:
    _get_client().put_object(
        Bucket=settings.r2_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def _delete_sync(key: str) -> None:
    try:
        _get_client().delete_object(Bucket=settings.r2_bucket, Key=key)
    except ClientError:
        pass


async def upload_file(key: str, data: bytes, content_type: str) -> str:
    """R2에 파일 업로드 후 public URL 반환"""
    await asyncio.to_thread(_upload_sync, key, data, content_type)
    return f"{settings.r2_public_url.rstrip('/')}/{key}"


async def delete_file(key: str) -> None:
    await asyncio.to_thread(_delete_sync, key)
