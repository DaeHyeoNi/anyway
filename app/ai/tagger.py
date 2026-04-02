import json
from datetime import date
from pathlib import Path

from google import genai
from google.genai import types

from app.config import settings

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
    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime),
            _get_system_prompt(),
        ],
        config=types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=200,
        ),
    )

    raw = response.text.strip()
    try:
        tags = json.loads(raw)
        if isinstance(tags, list):
            return [str(t).lower() for t in tags if isinstance(t, str)]
    except json.JSONDecodeError:
        pass
    return []
