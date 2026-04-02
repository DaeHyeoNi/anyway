from fastapi import HTTPException, Request


def get_current_admin(request: Request):
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=302, headers={"Location": "/manage/login"})
    return True


class RequireAdmin:
    """어드민 인증 의존성 — 미인증 시 로그인 페이지로 리다이렉트"""

    async def __call__(self, request: Request):
        if not request.session.get("is_admin"):
            raise HTTPException(status_code=302, headers={"Location": "/manage/login"})
