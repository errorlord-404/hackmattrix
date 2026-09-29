from __future__ import annotations

from pathlib import Path
import pytest

from app.core.config import settings
from app.services import kindwise_crop_health as provider


@pytest.mark.asyncio
async def test_kindwise_requires_server_side_configuration(tmp_path, monkeypatch):
    image = tmp_path / "leaf.png"; image.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    monkeypatch.setattr(settings, "KINDWISE_CROP_HEALTH_API_KEY", "")
    monkeypatch.setattr(settings, "KINDWISE_CROP_HEALTH_BASE_URL", "")
    result = await provider.assess_image(image, "tomato")
    assert result["status"] == "provider_unavailable"
    assert result["provider"] == "kindwise_crop_health"


@pytest.mark.asyncio
async def test_kindwise_normalizes_candidates_without_leaking_key(tmp_path, monkeypatch):
    image = tmp_path / "leaf.png"; image.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    monkeypatch.setattr(settings, "KINDWISE_CROP_HEALTH_API_KEY", "secret-key")
    monkeypatch.setattr(settings, "KINDWISE_CROP_HEALTH_BASE_URL", "https://provider.example")
    monkeypatch.setattr(settings, "KINDWISE_CROP_HEALTH_IDENTIFICATION_PATH", "/identify")

    def post(url, headers, payload, timeout):
        assert url == "https://provider.example/identify"
        assert headers == {"Api-Key": "secret-key"}
        assert set(payload) == {"images"}
        assert timeout == settings.KINDWISE_CROP_HEALTH_TIMEOUT_SECONDS
        return 200, b'{"result":{"disease":{"suggestions":[{"name":"Early blight","probability":0.81}]}}}'

    monkeypatch.setattr(provider, "_post_json", post)
    result = await provider.assess_image(image, "tomato")
    assert result["status"] == "completed"
    assert result["label"] == "Early blight"
    assert result["crop"] == "tomato"
    assert result["disease_candidates"][0]["score"] == 0.81
    assert "secret-key" not in str(result)


@pytest.mark.asyncio
async def test_kindwise_invalid_body_is_typed_unavailable(tmp_path, monkeypatch):
    image = tmp_path / "leaf.png"; image.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    monkeypatch.setattr(settings, "KINDWISE_CROP_HEALTH_API_KEY", "key")
    monkeypatch.setattr(settings, "KINDWISE_CROP_HEALTH_BASE_URL", "https://provider.example")

    monkeypatch.setattr(provider, "_post_json", lambda *_args: (200, b"not-json"))
    result = await provider.assess_image(image)
    assert result["status"] == "provider_unavailable"
    assert "invalid response" in result["error"]
