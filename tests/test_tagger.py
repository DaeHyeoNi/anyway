"""AI 태거 테스트"""
import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.ai.tagger import _get_system_prompt, generate_tags


# ── _get_system_prompt ───────────────────────────────────────────────────────

def test_system_prompt_contains_today():
    """프롬프트에 오늘 날짜 포함"""
    prompt = _get_system_prompt()

    assert str(date.today()) in prompt


def test_system_prompt_is_not_a_constant():
    """함수이므로 매 호출마다 평가 (모듈 고정 아님)"""
    # 두 번 호출해도 오늘 날짜 포함
    assert str(date.today()) in _get_system_prompt()
    assert str(date.today()) in _get_system_prompt()


# ── generate_tags ────────────────────────────────────────────────────────────

async def test_generate_tags_returns_empty_when_no_api_key(tmp_path):
    """API 키 없으면 빈 리스트 반환"""
    img_path = tmp_path / "test.jpg"
    Image.new("RGB", (10, 10)).save(img_path)

    with patch("app.ai.tagger.settings") as mock_settings:
        mock_settings.gemini_api_key = ""
        result = await generate_tags(img_path)

    assert result == []


async def test_generate_tags_returns_empty_on_api_failure(tmp_path):
    """Gemini API 예외 발생 시 빈 리스트 반환 (예외 전파 안 함)"""
    img_path = tmp_path / "test.jpg"
    Image.new("RGB", (10, 10)).save(img_path)

    with patch("app.ai.tagger.settings") as mock_settings:
        mock_settings.gemini_api_key = "fake-key"
        mock_settings.gemini_model = "test-model"
        with patch("app.ai.tagger._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.aio.models.generate_content = AsyncMock(
                side_effect=Exception("API Error 429")
            )
            mock_get_client.return_value = mock_client

            result = await generate_tags(img_path)

    assert result == []


async def test_generate_tags_returns_list_on_success(tmp_path):
    """정상 응답 → 태그 리스트 반환"""
    img_path = tmp_path / "test.jpg"
    Image.new("RGB", (10, 10)).save(img_path)

    mock_response = MagicMock()
    mock_response.text = json.dumps(["landscape", "mountain", "fog"])

    with patch("app.ai.tagger.settings") as mock_settings:
        mock_settings.gemini_api_key = "fake-key"
        mock_settings.gemini_model = "test-model"
        with patch("app.ai.tagger._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await generate_tags(img_path)

    assert result == ["landscape", "mountain", "fog"]


async def test_generate_tags_returns_empty_on_invalid_json(tmp_path):
    """JSON 파싱 실패 → 빈 리스트 반환"""
    img_path = tmp_path / "test.jpg"
    Image.new("RGB", (10, 10)).save(img_path)

    mock_response = MagicMock()
    mock_response.text = "이것은 JSON이 아닙니다"

    with patch("app.ai.tagger.settings") as mock_settings:
        mock_settings.gemini_api_key = "fake-key"
        mock_settings.gemini_model = "test-model"
        with patch("app.ai.tagger._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await generate_tags(img_path)

    assert result == []
