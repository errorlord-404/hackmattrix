# KisanSathi Electron farmer-lifecycle capability audit

This audit describes the original Electron application only. It is based on
the active desktop harness, KisanSathi MCP registry, backend farm-state API,
and renderer implementation. It is not a claim that a feature is available
merely because a model prompt mentions it.

## Available through the farmer chat

| Lifecycle need | Electron/Codex path | Guardrails |
| --- | --- | --- |
| First-use setup | `get_onboarding_status`, profile/field reads, and the silent bootstrap turn | Reads only; no field or profile is created without a preview and confirmation. |
| Field location and boundary | Farmer asks to open the field editor; an allowlisted UI action opens the polygon editor | The farmer draws the shape; an approximate pin remains explicitly labelled and is not a survey. |
| Crop/season selection | Field, soil, sensor, weather, crop-option, market, MSP, scheme, supplier, and live-web evidence workflows | Near-term weather is not presented as a whole-season forecast. |
| Care and irrigation | Observations, device freshness, forecast, irrigation screening, tasks, reminders, and recorded irrigation events | The app records farmer-confirmed work only; it does not actuate a pump or valve. |
| Crop health | In-chat photo attachment, farmer-scoped diagnosis record, image handoff, model evidence, current official-source verification, and farmer-confirmed diagnosis feedback | CNN output is triage only and cannot create a chemical recommendation by itself; feedback is a review lead, not automatic training or image export. |
| Weather/disaster/harvest | Field weather/alerts, open-session forecast polling, native desktop notifications for newly discovered in-app alerts, crop stage, tasks, harvest records, and current official relief research | Forecast risks are de-duplicated into the in-app alert inbox every 15 minutes while KisanSathi is open. Native alerts respect the farmer notification toggle and do not run after the app closes. |
| Machinery, inputs, schemes, exporters | Source-attributed directory, eligibility, comparison, and live-web research tools | Discovery does not book equipment, buy inputs, or guarantee stock/eligibility. |
| Mandi/logistics choice | Fresh price records plus `compare_sale_routes` using dated distance and complete provider/farmer cost quotes | The result is read-only and indicative; it cannot sell produce or book transport. |
| Financial records | Ledger, summary, explicit-input profit calculation, and report tools | No payment, transfer, credit, or loan action is exposed. |
| App navigation | Allowlisted Codex UI actions for fields, map, soil, weather, irrigation, tasks, disease, market, schemes, finance, machinery, marketplace, reports, settings, and device setup | Unknown actions cannot navigate anywhere. Development and packaged Electron routes are both supported. |

## Conversation and language contract

1. Sarvam transcribes with language auto-detection.
2. Local-language farmer input is translated to English before it reaches
   Codex.
3. Codex reasons and records its answer in English.
4. Codex provides a short `Farmer summary`; only that summary is translated
   and spoken in the detected Hindi or Marathi language.
5. Auto-speak is a conversation-wide setting, not a per-message requirement.

## Explicitly not yet deliverable without external capability

- A background service or mobile push/SMS channel for alerts when the desktop
  app is closed.
- Sensor provisioning, calibrated sensor guarantees, pump/valve control, or
  any physical equipment actuation.
- Booking machinery, purchasing inputs, filing a claim, export clearance,
  accepting buyer offers, selling produce, or moving money.
- A production disease decision from research-only model artifacts. Field/OOD
  validation, disease taxonomy approval, and agronomist review remain required
  before any such model can drive farm action.
- Guaranteed live availability, price, eligibility, inventory, contact
  validity, or external-source accuracy. The agent must report provider
  failures and stale data.

## Evidence and regression checks

- `agent/prompts/farmer_system_prompt.md`: farmer workflow, English-first
  language contract, research, confirmation, photo, and safety rules.
- `agent/src/kisansathi_agent/server.py`: farmer-scoped MCP registry.
- `agent/contracts/farmer_ui_tool_parity.json` and `agent/tests/test_ui_tool_parity.py`: every Electron farm-state mutation maps to a registered Codex tool or a documented human-only boundary for demo reset and secret entry.
- `desktop/codex-harness.cjs`: restricted Codex tool profile and session
  lifecycle.
- `src/context/AIConversationContext.jsx`: translation, speech, image,
  bootstrap, and allowlisted UI-action handling.
- `src/components/features/ai/uiNavigation.js`: browser/hash routing bridge
  for dev and packaged Electron.
- `npm run test:desktop`, focused Vitest suites, ESLint, and `npm run build`.

This audit should be updated whenever a backend provider, external delivery
channel, hardware integration, or production model release changes.
