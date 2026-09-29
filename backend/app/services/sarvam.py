from __future__ import annotations

import json
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings


class SarvamProviderError(RuntimeError):
    def __init__(self, message: str, *, code: str, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


def configured() -> bool:
    return bool(settings.SARVAM_API_KEY.strip())


def _safe_error_message(payload: object, fallback: str) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"][:300]
        if isinstance(payload.get("message"), str):
            return payload["message"][:300]
    return fallback


def _request_json(path: str, payload: dict) -> dict:
    if not configured():
        raise SarvamProviderError(
            "Sarvam API is not configured. Set SARVAM_API_KEY on the backend.",
            code="sarvam_not_configured",
        )
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{settings.SARVAM_BASE_URL.rstrip('/')}{path}",
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "api-subscription-key": settings.SARVAM_API_KEY,
        },
    )
    return _open_json(request)


def _open_json(request: Request) -> dict:
    try:
        with urlopen(request, timeout=settings.SARVAM_TIMEOUT_SECONDS) as response:
            raw = response.read()
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            payload = None
        status_code = exc.code
        raise SarvamProviderError(
            _safe_error_message(payload, "Sarvam API returned an error."),
            code=f"sarvam_http_{status_code}",
            retryable=status_code == 429 or status_code >= 500,
        ) from exc
    except (TimeoutError, URLError, OSError) as exc:
        raise SarvamProviderError(
            "Sarvam API is unreachable or timed out.",
            code="sarvam_unreachable",
            retryable=True,
        ) from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SarvamProviderError(
            "Sarvam API returned an invalid response.",
            code="sarvam_invalid_response",
        ) from exc
    if not isinstance(payload, dict):
        raise SarvamProviderError("Sarvam API returned an invalid response.", code="sarvam_invalid_response")
    return payload


def _multipart_body(
    *,
    audio: bytes,
    mime_type: str,
    filename: str,
    fields: dict[str, str],
) -> tuple[bytes, str]:
    boundary = f"----KisanSathiSarvam{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode("utf-8")
        )
    chunks.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8")
    )
    chunks.append(audio)
    chunks.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def transcribe_audio(
    audio: bytes,
    *,
    mime_type: str = "audio/webm",
    language_code: str | None = None,
    mode: str | None = None,
) -> dict:
    fields = {
        "model": settings.SARVAM_STT_MODEL,
        "mode": mode or settings.SARVAM_STT_MODE,
        "language_code": language_code or settings.SARVAM_STT_LANGUAGE_CODE,
        "with_timestamps": "false",
    }
    body, content_type = _multipart_body(
        audio=audio,
        mime_type=mime_type.split(";", 1)[0].strip() or "audio/webm",
        filename="voice-input.webm",
        fields=fields,
    )
    if not configured():
        raise SarvamProviderError(
            "Sarvam API is not configured. Set SARVAM_API_KEY on the backend.",
            code="sarvam_not_configured",
        )
    request = Request(
        f"{settings.SARVAM_BASE_URL.rstrip('/')}/speech-to-text",
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": content_type,
            "api-subscription-key": settings.SARVAM_API_KEY,
        },
    )
    return _open_json(request)


def synthesize_speech(
    text: str,
    *,
    language_code: str,
    speaker: str | None = None,
    model: str | None = None,
    pace: float | None = None,
    speech_sample_rate: int | None = None,
    output_audio_codec: str | None = None,
) -> dict:
    payload = {
        "text": text,
        "language_code": language_code,
        "speaker": speaker or settings.SARVAM_TTS_SPEAKER,
        "model": model or settings.SARVAM_TTS_MODEL,
        "pace": pace if pace is not None else settings.SARVAM_TTS_PACE,
        "speech_sample_rate": speech_sample_rate or settings.SARVAM_TTS_SPEECH_SAMPLE_RATE,
        "output_audio_codec": output_audio_codec or settings.SARVAM_TTS_CODEC,
    }
    result = _request_json("/text-to-speech", payload)
    audios = result.get("audios")
    if not isinstance(audios, list) or not audios or not isinstance(audios[0], str):
        raise SarvamProviderError("Sarvam TTS returned no audio.", code="sarvam_invalid_tts_response")
    return {"request_id": result.get("request_id"), "audio_base64": audios[0]}


def translate_text(
    text: str,
    *,
    source_language_code: str,
    target_language_code: str,
    model: str | None = None,
    mode: str | None = None,
    output_script: str | None = None,
) -> dict:
    payload = {
        "input": text,
        "source_language_code": source_language_code,
        "target_language_code": target_language_code,
        "model": model or settings.SARVAM_TRANSLATE_MODEL,
    }
    if mode:
        payload["mode"] = mode
    if output_script:
        payload["output_script"] = output_script
    return _request_json("/translate", payload)
