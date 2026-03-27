# Project Progress

> 이 파일은 long-term context 대응을 위한 프로젝트 진행 기록입니다.
> 새 대화 시작 시 이 파일을 먼저 참조하세요.

## 프로젝트 개요

| 항목 | 내용 |
|---|---|
| **프로젝트명** | anyway |
| **목적** | 개인 프로필 + 포토 갤러리 (풍경 사진 중심) |
| **운영 환경** | Raspberry Pi → 추후 Mac Mini 이전 예정 |
| **도메인** | daehyeoni.dev |
| **GitHub** | https://github.com/DaeHyeoNi/anyway |

## 사이트 구조

```
daehyeoni.dev/          → 프로필 (간단한 소개 + SNS 링크)
daehyeoni.dev/photos    → 포토 갤러리 그리드
daehyeoni.dev/photos/1  → 사진 상세 (EXIF, 태그, 색상 팔레트)
daehyeoni.dev/admin     → 업로드/관리 (비공개)
```

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Backend | FastAPI + SQLAlchemy (async) + Alembic |
| Frontend | Jinja2 + HTMX + Tailwind CSS + Alpine.js |
| Database | SQLite → PostgreSQL (필요시) |
| Storage | 로컬 파일시스템 → Cloudflare R2 (CDN, 무료 10GB) |
| AI | GPT-4o mini Vision (업로드 시 자동 태깅, 1회성) |
| Package | uv |
| Infra | Docker Compose + Nginx + Let's Encrypt |

## 디렉토리 구조 (목표)

```
anyway/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── photos/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── ai/
│   │   ├── tagger.py          # GPT-4o mini Vision 태그 생성
│   │   └── analyzer.py        # EXIF 파싱, 색상 팔레트 추출
│   ├── admin/
│   │   └── router.py
│   └── templates/
│       ├── base.html
│       ├── photos/
│       │   ├── index.html
│       │   ├── detail.html
│       │   └── _grid_item.html  # HTMX partial
│       └── admin/
│           └── upload.html
├── static/
├── storage/
│   ├── originals/
│   └── thumbnails/
├── migrations/
├── tests/
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## DB 스키마 (목표)

```sql
photos
  id, filename, title, description
  taken_at            -- EXIF 날짜
  location            -- EXIF GPS → 지명 변환
  camera, lens, aperture, shutter_speed, iso
  width, height, file_size
  storage_url         -- R2 or 로컬 경로
  thumb_url
  ai_tags             -- JSON ["landscape", "golden hour", ...]
  color_palette       -- JSON ["#f2c94c", "#2d9cdb", ...]
  is_published
  created_at

albums
  id, title, slug, cover_photo_id, description

album_photos
  album_id, photo_id, order
```

## 로드맵

### Phase 1 — MVP
- [x] 프로젝트 스캐폴딩 (uv, FastAPI, Alembic)
- [x] DB 모델 & 마이그레이션 (photos, albums)
- [x] 사진 업로드 API (리사이징 + 썸네일 자동 생성)
- [x] EXIF 자동 파싱 (촬영일, 카메라, GPS)
- [x] 갤러리 그리드 뷰 (Jinja2 + Tailwind)
- [x] 사진 상세 페이지
- [x] 어드민 업로드 UI (드래그앤드롭, 다중 업로드)

### Phase 2 — AI 연동
- [ ] GPT-4o mini Vision 자동 태그 생성
- [ ] Pillow 색상 팔레트 추출
- [ ] GPS → 지명 변환 (reverse geocoding)
- [ ] 유사 사진 추천

### Phase 3 — UX
- [ ] 앨범/컬렉션 구성
- [ ] 태그 필터링 (HTMX)
- [ ] 지도 뷰 (촬영 위치)
- [ ] EXIF 정보 오버레이

### Phase 4 — 인프라
- [ ] Cloudflare R2 연동 (Standard 스토리지, 버킷: anyway-photos) — Pi 배포 시점에 진행
- [ ] 로컬 storage/ → R2 마이그레이션 스크립트
- [ ] Nginx 리버스 프록시
- [ ] Docker Compose 완성
- [ ] Raspberry Pi 배포

## 진행 로그

| 날짜 | 내용 |
|---|---|
| 2026-03-27 | 프로젝트 기획 완료. 스택 확정: FastAPI + Jinja2/HTMX + SQLite + GPT-4o mini |
| 2026-03-27 | Phase 1 스캐폴딩 완료. FastAPI 서버 구동 확인, DB 마이그레이션 적용 |
| 2026-03-27 | Phase 1 완료. 업로드 파이프라인(EXIF, 썸네일, 색상팔레트), 어드민 로그인(/manage) 구현 |

## 미결 사항

- [x] Cloudflare R2 버킷 생성 완료 (Standard, anyway-photos) — Pi 배포 시 코드 연동 예정
- [ ] OpenAI API 키 준비
