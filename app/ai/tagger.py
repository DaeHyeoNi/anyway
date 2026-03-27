import base64
from datetime import date
from pathlib import Path

from openai import AsyncOpenAI

from app.config import settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


SYSTEM_PROMPT = f"""You are a photography tagging assistant. Today is {date.today()}.
Analyze the provided photo and return relevant tags only.

Rules:
- Return ONLY a JSON array of lowercase English tags, nothing else
- Use only information visible in the image — no inference or fabrication
- Include: subject, mood, lighting, season, weather, location type if identifiable
- 8 to 15 tags per image
- Example: ["landscape", "mountains", "golden hour", "misty", "autumn", "wide angle"]"""


async def generate_tags(image_path: Path) -> list[str]:
    if not settings.openai_api_key:
        return []

    image_data = base64.standard_b64encode(image_path.read_bytes()).decode()
    suffix = image_path.suffix.lower()
    mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else f"image/{suffix.lstrip('.')}"

    client = _get_client()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{image_data}", "detail": "low"},
                    }
                ],
            },
        ],
        max_tokens=200,
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()

    import json
    try:
        tags = json.loads(raw)
        if isinstance(tags, list):
            return [str(t).lower() for t in tags if isinstance(t, str)]
    except json.JSONDecodeError:
        pass
    return []
