"""RequireAdmin 인증 의존성 테스트"""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Request

from app.auth.deps import RequireAdmin, get_current_admin


async def test_require_admin_raises_when_unauthenticated():
    """미인증 시 HTTPException(302) raise"""
    require_admin = RequireAdmin()
    request = MagicMock(spec=Request)
    request.session = {}

    with pytest.raises(HTTPException) as exc_info:
        await require_admin(request)

    assert exc_info.value.status_code == 302
    assert exc_info.value.headers["Location"] == "/manage/login"


async def test_require_admin_passes_when_authenticated():
    """인증 시 예외 없이 통과"""
    require_admin = RequireAdmin()
    request = MagicMock(spec=Request)
    request.session = {"is_admin": True}

    await require_admin(request)  # 예외 없으면 통과


def test_get_current_admin_raises_when_unauthenticated():
    """get_current_admin: 미인증 시 HTTPException(302) raise"""
    request = MagicMock(spec=Request)
    request.session = {}

    with pytest.raises(HTTPException) as exc_info:
        get_current_admin(request)

    assert exc_info.value.status_code == 302


def test_get_current_admin_returns_true_when_authenticated():
    """get_current_admin: 인증 시 True 반환"""
    request = MagicMock(spec=Request)
    request.session = {"is_admin": True}

    result = get_current_admin(request)

    assert result is True
