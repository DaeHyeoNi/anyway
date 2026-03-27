# Project Progress

> 이 파일은 long-term context 대응을 위한 프로젝트 진행 기록입니다.
> 새 대화 시작 시 이 파일을 먼저 참조하세요.

## 프로젝트 개요

| 항목 | 내용 |
|---|---|
| **프로젝트명** | anyway |
| **목적** | 개인 프로필 + 포토 갤러리 (풍경/여행 사진 중심) |
| **운영 환경** | Raspberry Pi (현재 운영 중) → 추후 Mac Mini 이전 예정 |
| **도메인** | daehyeoni.dev |
| **미디어 CDN** | media.daehyeoni.dev (Cloudflare R2 커스텀 도메인) |
| **GitHub** | https://github.com/DaeHyeoNi/anyway |

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Backend | FastAPI + SQLAlchemy async + Alembic |
| Frontend | Jinja2 + HTMX + Tailwind CSS (CDN) + Alpine.js (CDN) |
| Database | SQLite (aiosqlite) |
| Storage | Cloudflare R2 (운영 중, 버킷: photos, 도메인: media.daehyeoni.dev) |
| AI 태깅 | Gemini gemini-3.1-flash-preview (업로드 후 백그라운드 처리) |
| Geocoding | Nominatim (reverse/forward, 무료) |
| Package | uv |
| Infra | Docker Compose + 시스템 Nginx (리버스 프록시) + Raspberry Pi |
| Analytics | Google Tag Manager (GTM-WQT2Q7ZJ) |

## 사이트 구조

```
daehyeoni.dev/           → 프로필 (간단한 소개 + SNS 링크)
daehyeoni.dev/photos/    → 포토 갤러리 그리드 (나라별 필터, 모달 뷰어)
daehyeoni.dev/photos/map → 지도 뷰 (GPS 좌표 기반 Leaflet)
daehyeoni.dev/tools/     → 도구 모음
daehyeoni.dev/manage/    → 어드민 (로그인 필요)
```

## DB 스키마 (현재)

```
photos
  id, filename, title, description
  taken_at                  -- EXIF 날짜
  location                  -- GPS → 지명 (Nominatim reverse geocode)
  latitude, longitude       -- GPS 좌표 (지도 뷰용)
  camera, lens, focal_length, aperture, shutter_speed, iso
  width, height, file_size
  storage_url, thumb_url    -- R2 URL 또는 로컬 /storage/... 경로
  ai_tags                   -- JSON ["landscape", "city", ...]
  color_palette             -- JSON ["#f2c94c", ...]
  is_published
  created_at
```

## 디렉토리 구조 (현재)

```
anyway/
├── app/
│   ├── main.py
│   ├── config.py          # pydantic-settings, extra="ignore"
│   ├── database.py
│   ├── storage.py         # Cloudflare R2 (boto3 S3 호환)
│   ├── photos/
│   │   ├── router.py      # /photos/, /photos/map, /photos/{id}/data
│   │   ├── service.py     # create_photo_from_upload, tag_and_cleanup(BG)
│   │   └── models.py
│   ├── ai/
│   │   ├── tagger.py      # Gemini Vision 태그 생성
│   │   └── analyzer.py    # EXIF, 색상팔레트, reverse/forward geocode
│   ├── admin/
│   │   └── router.py      # /manage/* (hmac 인증)
│   └── templates/
│       ├── base.html      # GTM 포함
│       ├── photos/
│       │   ├── index.html # 갤러리 그리드 + 나라 필터 + 모달
│       │   ├── map.html   # Leaflet 지도
│       │   └── _grid.html
│       └── admin/
│           ├── login.html
│           ├── dashboard.html
│           ├── upload.html  # Alpine.js EXIF 자동채우기 + FormData submit
│           ├── photos.html
│           └── edit.html    # 섹션별 편집 (기본/촬영/위치)
├── migrations/
│   └── versions/
│       ├── 936ae0bfe554_init.py
│       └── 96ba7619e2a1_add_focal_length_to_photos.py
├── scripts/
│   ├── start.sh              # 마이그레이션 후 uvicorn 시작
│   ├── migrate_to_r2.py      # 로컬 → R2 일괄 마이그레이션
│   └── geocode_locations.py  # location 텍스트 → GPS 좌표 일괄 변환
├── nginx/
│   └── anyway.conf           # 시스템 nginx 설정 (proxy_pass :PORT)
├── debug_gps.py
├── deploy.sh                 # git pull + docker compose up --build
├── log.sh                    # docker compose logs app -f
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── pyproject.toml
```

## 환경변수 (.env)

```
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:////app/anyway.db
STORAGE_PATH=/app/storage
PORT=<호스트 바인딩 포트>

ADMIN_ID=...
ADMIN_PASSWORD=...
SECRET_KEY=...

GEMINI_API_KEY=...

R2_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com
R2_ACCESS_KEY=...
R2_SECRET_KEY=...
R2_BUCKET=photos
R2_PUBLIC_URL=https://media.daehyeoni.dev
```

## 주요 동작 흐름

### 업로드
1. 파일 선택 → Alpine.js가 `/manage/photos/exif`로 EXIF 파싱 요청 (폼 자동 채우기)
2. 업로드 버튼 → Alpine.js가 `FormData` 직접 구성하여 POST (file input 초기화 버그 우회)
3. `create_photo_from_upload`: 썸네일 생성 → EXIF 파싱 → R2 업로드 → DB 저장
4. `tag_and_cleanup` (BackgroundTasks): Gemini AI 태깅 → DB 업데이트 → 로컬 파일 정리

### 갤러리
- 나라별 필터 (location 마지막 쉼표 뒤 country 추출)
- 사진 클릭 → `/photos/{id}/data` 호출 → Alpine.js 모달 표시
- HTMX로 필터 시 그리드 부분 교체

### 지도
- `latitude`/`longitude` 있는 사진만 표시
- 수정 페이지에서 직접 입력 또는 location 텍스트로 forward geocoding 자동 변환

## 알려진 이슈 / 특이사항

- 중국에서 찍은 삼성폰 사진은 GPS가 법적으로 비워짐 → 위치 수동 입력 필요
- EXIF fetch 후 file input이 초기화되는 Alpine.js 버그 → FormData 직접 구성으로 해결
- Nominatim rate limit: geocode_locations.py 실행 시 1초 딜레이 적용

## 로드맵

### 완료
- [x] Phase 1 MVP (업로드, 갤러리, EXIF, 어드민)
- [x] Phase 2 AI 연동 (Gemini 태깅, 색상팔레트, GPS geocoding)
- [x] Phase 3 UX (모달 뷰어, 나라 필터, 지도, EXIF 오버레이)
- [x] Phase 4 인프라 (R2 연동, Docker Compose, Nginx, Pi 배포)
- [x] 사진 수정/삭제, 태그 편집, 좌표 직접 입력
- [x] 업로드 non-blocking (AI 태깅 BackgroundTasks)
- [x] Google Tag Manager

### 미정 / 추후
- [ ] TOTP 2단계 인증
- [ ] Mac Mini 이전
- [ ] 앨범/컬렉션 기능 (모델은 있음)

## 진행 로그

| 날짜 | 내용 |
|---|---|
| 2026-03-27 | 프로젝트 기획 및 Phase 1~3 구현 완료 |
| 2026-03-27 | Phase 4: Docker Compose, Nginx, Raspberry Pi 배포 |
| 2026-03-27 | Cloudflare R2 연동 (media.daehyeoni.dev), 마이그레이션 스크립트 |
| 2026-03-27 | 사진 수정 UI 개선 (섹션 분리, 초점거리, 좌표 입력, 태그 편집) |
| 2026-03-27 | forward geocoding 추가, 나라 필터로 교체, GTM 설치 |
| 2026-03-27 | 업로드 버그 수정 (0 bytes, HEIC 지원), AI 태깅 백그라운드 처리 |
