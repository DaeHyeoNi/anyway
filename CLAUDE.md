# Claude Instructions — anyway

## 시작 시 필수 확인

새 대화를 시작할 때 **반드시 `PROGRESS.md`를 먼저 읽고** 프로젝트 현황을 파악한 후 작업을 시작하세요.

## 작업 규칙

- 작업 완료 후 `PROGRESS.md`의 진행 로그와 로드맵을 최신 상태로 업데이트하세요.
- 커밋은 작업 완료 후 반드시 수행합니다 (CLAUDE.md 전역 규칙 준수).
- 배포는 `./deploy.sh`, 로그 확인은 `./log.sh`를 사용합니다.
- Pi에서 실행 시 Docker 컨테이너 내부에서: `docker compose exec app <명령>`

## 주요 경로

| 용도 | 경로 |
|---|---|
| 앱 진입점 | `app/main.py` |
| 설정 | `app/config.py` |
| R2 스토리지 | `app/storage.py` |
| 사진 서비스 | `app/photos/service.py` |
| 어드민 라우터 | `app/admin/router.py` |
| AI 분석 | `app/ai/analyzer.py`, `app/ai/tagger.py` |
| 템플릿 | `app/templates/` |
| 유틸 스크립트 | `scripts/` |
