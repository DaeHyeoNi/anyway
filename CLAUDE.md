# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 시작 시 필수 확인

새 대화를 시작할 때 **반드시 `PROGRESS.md`를 먼저 읽고** 프로젝트 현황을 파악한 후 작업을 시작하세요.

## 개발 명령어

```bash
# 개발 서버 실행
uv run uvicorn app.main:app --reload --port 8080

# DB 마이그레이션
uv run alembic upgrade head

# 새 마이그레이션 생성 (모델 변경 후)
uv run alembic revision --autogenerate -m "설명"

# GPS 디버그
uv run python debug_gps.py <이미지경로>

# 로컬 → R2 마이그레이션
uv run python scripts/migrate_to_r2.py

# location 텍스트 → GPS 좌표 일괄 변환
uv run python scripts/geocode_locations.py
```

## 배포 (Raspberry Pi)

```bash
./deploy.sh     # git pull + docker compose up -d --build --remove-orphans
./log.sh        # docker compose logs app -f

# 컨테이너 내부 실행
docker compose exec app uv run <명령>
```

## 아키텍처

### 요청 흐름

```
브라우저
  └─ Nginx (시스템, 포트 80)
       └─ Docker app (127.0.0.1:PORT → 컨테이너 내부 :8080)
            └─ FastAPI (app/main.py)
                 ├─ /photos/*   → app/photos/router.py
                 ├─ /manage/*   → app/admin/router.py
                 └─ /tools/*    → app/tools/router.py
```

### 업로드 파이프라인

```
POST /manage/photos/upload
  1. file.seek(0) + file.read()          ← Alpine FormData로 전송 (file input 버그 우회)
  2. create_photo_from_upload()
     - Pillow 포맷 검증 (HEIC 포함)
     - 썸네일 생성 (BytesIO → JPEG)
     - EXIF 파싱 (piexif)
     - 색상 팔레트 추출 (Pillow quantize)
     - reverse geocode (Nominatim, GPS 있을 때)
     - R2 업로드 또는 로컬 저장
     - DB 저장 (ai_tags=None)
  3. BackgroundTasks: tag_and_cleanup()
     - Gemini Vision API → ai_tags 업데이트
     - R2 사용 시 로컬 파일 삭제
```

### 스토리지 전략

- `is_r2_enabled()` True이면 R2에 업로드, 로컬 파일은 태깅 완료 후 삭제
- False이면 `storage/originals/`, `storage/thumbnails/` 로컬 저장
- `storage_url` / `thumb_url` 컬럼에 전체 URL 저장 (R2: `https://media.daehyeoni.dev/...`, 로컬: `/storage/...`)

### 어드민 인증

`app/auth/deps.py`의 `RequireAdmin`이 세션 쿠키 검사.
반환값이 `RedirectResponse`인지 체크하는 패턴이 각 엔드포인트에 있음:
```python
if isinstance(_, RedirectResponse):
    return _
```

### 주요 설계 결정

- **EXIF 자동채우기**: 파일 선택 시 `/manage/photos/exif`로 별도 요청 → Alpine `this.files`에 File 객체 보관. 폼 submit 시 file input이 초기화되므로 `@submit.prevent`로 가로채서 `FormData` 직접 구성
- **나라 필터**: `location` 컬럼의 마지막 `, Country` 부분 추출. HTMX로 그리드 부분 교체
- **지도**: `latitude`/`longitude` 있는 사진만 표시. location 텍스트 저장 시 forward geocode로 자동 변환
- **pydantic-settings**: `extra="ignore"` 설정 — `.env`의 `PORT` 등 앱 외 변수가 ValidationError 유발하지 않도록

## 모델 변경 시 주의

1. `app/photos/models.py` 수정
2. `uv run alembic revision --autogenerate -m "..."` 으로 마이그레이션 생성
3. `uv run alembic upgrade head` 로 로컬 적용
4. 마이그레이션 파일(`migrations/versions/`) 커밋 포함
