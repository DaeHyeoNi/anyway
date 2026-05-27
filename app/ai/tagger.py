import json
import logging
from datetime import date
from pathlib import Path

from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _get_system_prompt() -> str:
    return f"""You are a photography tagging assistant. Today is {date.today()}.
Analyze the provided photo and return relevant tags only.

Rules:
- Return ONLY a JSON array of lowercase English tags, nothing else
- Use only information visible in the image — no inference or fabrication
- Include: subject, mood, lighting, season, weather, location type if identifiable
- 8 to 15 tags per image
- Example: ["landscape", "mountains", "golden hour", "misty", "autumn", "wide angle"]"""


async def generate_tags(image_path: Path) -> list[str]:
    if not settings.gemini_api_key:
        return []

    image_bytes = image_path.read_bytes()
    suffix = image_path.suffix.lower()
    mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else f"image/{suffix.lstrip('.')}"

    client = _get_client()
    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime),
                _get_system_prompt(),
            ],
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=300,
                response_mime_type="application/json",
            ),
        )
    except Exception as e:
        logger.error("Gemini API 호출 실패: %s", e)
        return []

    # 1. response.parsed가 혹시라도 확보되어 있다면 우선 사용 (하이브리드 대응)
    try:
        parsed_val = getattr(response, "parsed", None)
        if parsed_val is not None:
            if isinstance(parsed_val, list):
                logger.info("Gemini 응답이 response.parsed를 통해 즉시 파이썬 리스트로 확보되었습니다: %r", parsed_val)
                return [str(t).lower() for t in parsed_val if t]
    except Exception as parse_err:
        logger.warning("response.parsed 확인 실패: %s", parse_err)

    # 2. response.text 안전하게 추출
    text_val = getattr(response, "text", None)
    if text_val is None:
        logger.warning("Gemini 응답의 text 필드가 None입니다. 상세 응답 객체: %r", response)
        return []

    raw = text_val.strip()
    
    # 1차 디펜스: 만약 응답에 마크다운 백틱 펜스(```json ...)가 포함된 경우 디펜스 정제 실행
    if "```" in raw:
        import re
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw, re.DOTALL)
        if match:
            raw = match.group(1).strip()

    # 2차 디펜스: 혹시 모를 pre-amble 설명 문구 차단 및 JSON Array 영역([ ... ])만 강제 발췌
    if not raw.startswith("["):
        import re
        match = re.search(r'(\[.*?\])', raw, re.DOTALL)
        if match:
            raw = match.group(1).strip()

    try:
        tags = json.loads(raw)
        if isinstance(tags, list):
            return [str(t).lower() for t in tags if isinstance(t, str)]
    except json.JSONDecodeError as jde:
        logger.error("Gemini 응답 JSON 파싱 실패 (원시 데이터: %r): %s", raw, jde)
        pass
    return []
