# Offline + connected advisor contract

Every KisanSathi capability has two explicit paths.

## Offline path

- A screen may use only stored farmer-local observations plus a versioned,
  configurable rule or knowledge catalogue.
- It must show the catalogue/rule source, inputs, bounds, and uncertainty.
- It must not imply fresh weather, market, provider, disease, or web research.
- It must never control hardware or perform an external action.

## Connected path

- A farmer-initiated manual-screen review uses
  `requestAdvisorReview({ workflow, fieldId, prompt })` from
  `AIConversationContext`.
- The shared gateway queues the request into the same Electron/Codex
  farmer-scoped conversation as typed and voice chat, using `input_via: ui-*`.
- The advisor reads only the farmer-safe KisanSathi tools needed for the
  workflow, obtains current evidence where tools support it, and returns the
  answer in the chat transcript.
- A connected answer must distinguish stored/local data from refreshed source
  data and must retain confirmation for writes, bookings, payments, messages,
  and every real-world action.

## Implementation rule for new screens

1. Build the deterministic offline rule/catalogue first and label it in UI.
2. Add a clear “Ask AI to review” connected action using the shared gateway.
3. Give the advisor a workflow-specific prompt naming the selected field,
   required evidence, uncertainty, and safe action boundary.
4. Add a test for both the local path and the `ui-*` connected handoff.

The browser-only build has no local Codex harness. It remains an offline/manual
viewer until a separately configured server-side advisor is provided; it must
not pretend that an agent ran. The Electron app is the supported connected
advisor host today.
