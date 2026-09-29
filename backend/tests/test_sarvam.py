import json

from app.core.config import settings
from app.services import sarvam


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.payload


def test_sarvam_rest_shapes_and_secret_header(monkeypatch):
    requests = []
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "test-secret")

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        if request.full_url.endswith("/text-to-speech"):
            return _Response({"request_id": "tts-1", "audios": ["UklGRg=="]})
        if request.full_url.endswith("/translate"):
            return _Response({"request_id": "translate-1", "translated_text": "Hello", "source_language_code": "hi-IN"})
        return _Response({"request_id": "stt-1", "transcript": "नमस्ते", "language_code": "hi-IN"})

    monkeypatch.setattr(sarvam, "urlopen", fake_urlopen)
    tts = sarvam.synthesize_speech("नमस्ते", language_code="hi-IN")
    translation = sarvam.translate_text("नमस्ते", source_language_code="hi-IN", target_language_code="en-IN")
    stt = sarvam.transcribe_audio(b"audio", mime_type="audio/webm")

    assert tts["audio_base64"] == "UklGRg=="
    assert translation["translated_text"] == "Hello"
    assert stt["transcript"] == "नमस्ते"
    assert len(requests) == 3
    for request, timeout in requests:
        assert request.get_header("Api-subscription-key") == "test-secret"
        assert timeout == settings.SARVAM_TIMEOUT_SECONDS
    tts_payload = json.loads(requests[0][0].data)
    assert tts_payload["model"] == "bulbul:v3"
    assert tts_payload["language_code"] == "hi-IN"
    assert b"name=\"file\"" in requests[2][0].data
    assert b"name=\"model\"" in requests[2][0].data
