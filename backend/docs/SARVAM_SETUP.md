# Sarvam AI voice setup

The backend now supports Sarvam's REST APIs for:

- Saaras speech-to-text at `/speech-to-text`
- Bulbul text-to-speech at `/text-to-speech`
- Sarvam text translation at `/translate`

The combined KisanSathi voice route is `POST /v1/voice/turns`. Direct
capability routes are `POST /v1/voice/transcribe`,
`POST /v1/voice/synthesize`, and `POST /v1/translate`.

## Configure locally

Copy the values into `backend/.env` (never commit that file):

```dotenv
SARVAM_API_KEY=replace-with-your-dashboard-key
VOICE_PROVIDER=sarvam
SARVAM_STT_MODEL=saaras:v3
SARVAM_STT_MODE=transcribe
SARVAM_STT_LANGUAGE_CODE=unknown
SARVAM_TTS_MODEL=bulbul:v3
SARVAM_TTS_SPEAKER=shubh
SARVAM_TTS_PACE=1.0
SARVAM_TTS_SPEECH_SAMPLE_RATE=24000
SARVAM_TTS_CODEC=wav
SARVAM_TRANSLATE_MODEL=mayura:v1
```

Restart FastAPI after changing `.env`. The key is sent only in the backend
request header and is never returned in API responses.

Short browser recordings are supported by the synchronous REST STT endpoint;
long recordings should use Sarvam's batch API instead. The voice route returns
an explicit unavailable/inconclusive state when the key, provider, or upstream
service is not ready.

Official references:

- https://docs.sarvam.ai/api-reference/speech-to-text/transcribe
- https://docs.sarvam.ai/api-reference/text-to-speech/convert
- https://docs.sarvam.ai/api-reference/text/translate-text
