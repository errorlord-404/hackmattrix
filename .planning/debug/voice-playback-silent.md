---
status: investigating
trigger: "cant hear the playback voice"
created: 2026-09-26
updated: 2026-09-26
---

# Voice playback is silent

## Symptoms

- expected: Pressing Speak/playback reads the farmer explanation aloud.
- actual: No audible voice playback.
- errors: No error message reported by the user.
- timeline: Reported after restarting the Electron app during the full-access harness fix.
- reproduction: Generate an agent response and press the Speak/playback control.

## Current Focus

- hypothesis: Electron is muted or routed incorrectly in the Windows per-app audio mixer; synthesis itself is healthy.
- test: Compare a direct Windows SoundPlayer playback with Electron's Speak playback.
- expecting: If direct playback is audible, the fault is isolated to Electron's audio session; if silent, it is the Windows output device or master audio path.
- next_action: ask whether the direct Windows diagnostic sentence was audible

## Evidence

- timestamp: 2026-09-26T00:00:00+05:30
  observation: Backend health reports Sarvam configured.
- timestamp: 2026-09-26T00:00:01+05:30
  observation: POST /v1/voice/synthesize completed and returned audio/wav with 114748 base64 characters.
- timestamp: 2026-09-26T00:00:02+05:30
  observation: Decoded response is a RIFF/WAVE file with non-zero sample bytes.
- timestamp: 2026-09-26T00:00:03+05:30
  observation: Windows Audio and AudioEndpointBuilder services are running; SoundPlayer completed playback without an API error.

## Eliminated

- hypothesis: Missing or invalid Sarvam API key.
  reason: Live TTS request succeeds.
- hypothesis: Provider returned empty or structurally invalid audio.
  reason: Valid non-silent RIFF/WAVE bytes were returned.

## Resolution

- root_cause:
- fix:
- verification:
- files_changed:
