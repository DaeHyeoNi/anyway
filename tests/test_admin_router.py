"""어드민 라우터 통합 테스트"""
import pytest


# ── 인증 리다이렉트 ──────────────────────────────────────────────────────────

async def test_dashboard_redirects_when_unauthenticated(client):
    """미인증 → /manage 접근 시 302 리다이렉트"""
    resp = await client.get("/manage", follow_redirects=False)

    assert resp.status_code == 302
    assert "/manage/login" in resp.headers["location"]


async def test_upload_page_redirects_when_unauthenticated(client):
    """미인증 → 업로드 페이지 302 리다이렉트"""
    resp = await client.get("/manage/photos/upload", follow_redirects=False)

    assert resp.status_code == 302


async def test_photo_list_redirects_when_unauthenticated(client):
    """미인증 → 사진 목록 302 리다이렉트"""
    resp = await client.get("/manage/photos", follow_redirects=False)

    assert resp.status_code == 302


async def test_edit_page_redirects_when_unauthenticated(client):
    """미인증 → 편집 페이지 302 리다이렉트"""
    resp = await client.get("/manage/photos/1/edit", follow_redirects=False)

    assert resp.status_code == 302


# ── 로그아웃 메서드 ──────────────────────────────────────────────────────────

async def test_logout_get_returns_405(client):
    """GET /manage/logout → 405 (POST 전용)"""
    resp = await client.get("/manage/logout")

    assert resp.status_code == 405


async def test_logout_post_clears_session(client):
    """POST /manage/logout → 세션 클리어 후 로그인 페이지로 리다이렉트"""
    resp = await client.post("/manage/logout", follow_redirects=False)

    assert resp.status_code == 302
    assert "/manage/login" in resp.headers["location"]


# ── 갤러리 라우터 ────────────────────────────────────────────────────────────

async def test_photo_detail_returns_404_for_missing_photo(client):
    """존재하지 않는 photo_id → 404"""
    resp = await client.get("/photos/99999")

    assert resp.status_code == 404


async def test_photo_data_returns_404_for_missing_photo(client):
    """존재하지 않는 photo_id data 엔드포인트 → 404"""
    resp = await client.get("/photos/99999/data")

    assert resp.status_code == 404


async def test_photo_list_returns_200(client):
    """갤러리 메인 → 200 (빈 DB여도 정상)"""
    resp = await client.get("/photos/")

    assert resp.status_code == 200


async def test_photo_list_wildcard_country_filter(client):
    """country 파라미터에 % 포함해도 500 에러 없음"""
    resp = await client.get("/photos/?country=%25")

    assert resp.status_code == 200
