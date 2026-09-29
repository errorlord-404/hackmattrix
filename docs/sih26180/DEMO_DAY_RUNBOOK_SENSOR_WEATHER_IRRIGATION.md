# Demo-day runbook: sensor + weather-aware irrigation

## Purpose

Present one reliable, honest story:

> KisanSathi reads field-scoped soil moisture, refreshes the matching short
> forecast, and explains whether to irrigate, hold water, or use only a small
> emergency split. It does not operate a pump.

The primary demo source is the built-in Tomato simulator. It writes normal
sensor records with `simulation:tomato-demo:v1`, so the dashboard and agent use
the same contracts as a later device gateway. Never call it live hardware.

## Demo paths

| Path | Use when | Evidence label | Expected outcome |
| --- | --- | --- | --- |
| Water-stress + ordinary/no rain | Live forecast is available and does not indicate heavy rain | Tomato prototype simulation + provider forecast | Normal advisory irrigation (100% of calibrated normal amount) |
| Water-stress + heavy rain | A prepared, labelled forecast fixture is available | Tomato prototype simulation + labelled demo forecast | `defer_for_heavy_rain`, 0% application, drainage check |
| Critically dry + heavy rain | A prepared, labelled forecast fixture is available | Tomato prototype simulation + labelled demo forecast | `reduce_for_heavy_rain`, 25% emergency split only if stress is visible |
| Offline fallback | Weather provider is unavailable | Tomato prototype simulation; forecast unavailable | Do not claim rain-aware optimisation; explain that forecast evidence is missing |

Do not promise the heavy-rain branch from a live forecast on a day without a
heavy-rain signal. Use a clearly visible fixture for that branch, or present
the ordinary-rain path instead.

## One-time preparation (the day before)

1. Install dependencies once and run the verification suite:

   ```powershell
   cd "C:\Users\prana\Desktop\sih mvp"
   npm run build
   cd backend
   python -m pytest tests/test_irrigation_rules.py tests/test_farm_state.py -q
   cd ..\agent
   python -m pytest tests/test_tools.py -q
   ```

2. Prepare two browser windows: the KisanSathi dashboard and the AI/Voice
   Assistant. Sign in or otherwise confirm the selected farmer is `demo`.
3. Create/select one field named clearly for the presentation, with Tomato as
   the active crop and a valid boundary. This gives weather a field-specific
   coordinate; never use another field's forecast.
4. Rehearse the exact sequence below once. Keep a screenshot of the expected
   `water-stress` values as a visual fallback.
5. If a heavy-rain narrative is essential, use the Tomato simulator card's
   **Heavy rain · 30 mm / 48h** button. It writes an explicit, field-scoped
   simulation fixture; the card displays its active state. Use **Use live
   weather** to clear only that demo fixture. Never present fixture rainfall as
   live weather.

## Start procedure (15 minutes before presenting)

From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-demo.ps1 -ResetDemo
```

This starts MongoDB when available, the FastAPI backend on port 8001, Vite on
an available port, Electron, and enables `TOMATO_DEMO_ENABLED=true` only for
this launch. It also leaves the app usable when Mongo/reference refresh is
unavailable.

Perform this short preflight before showing the audience:

- Open the field dashboard and confirm **Tomato prototype simulation** is
  visibly labelled.
- Open the Tomato demo control; select `water-stress`, start it, and wait one
  15-second tick.
- Confirm moisture, observed time, source, pH, EC, and NPK are visible. State
  that simulated NPK is a prototype scenario, not Wokwi hardware evidence.
- In the Weather page or agent, refresh weather for the selected field. Check
  the provider/source and fetched time.
- Open the Irrigation page and confirm its recommendation includes assumptions
  about both moisture and forecast. Verify the app says it does not control a
  pump or valve.
- If crop-health is part of the presentation, confirm its API configuration
  first. Otherwise show the typed `provider_unavailable` result rather than
  retrying or pretending diagnosis worked.

## Four-minute presentation script

### 1. Establish the evidence (45 seconds)

Open the selected Tomato field. Say: “The hardware delivery is delayed, so
this is a source-labelled Tomato simulation running through the real sensor
observation path. When the physical node arrives it will publish to the same
contract.” Point out moisture, timestamp, and `simulation:tomato-demo:v1`.

### 2. Ask the farmer question (45 seconds)

In chat: “Should I water the Tomato field today?”

The agent must resolve the exact field, refresh field weather, call irrigation
advice, and explain source, moisture, forecast horizon, and the next step. It
must not claim a pump has started.

### 3. Show normal water-stress decision (45 seconds)

With low moisture and no heavy-rain condition, show the normal advisory. Say:
“The app may say 100% of the calibrated normal application, but it deliberately
does not fabricate litres or duration because this demo has no verified flow
calibration.”

### 4. Show rain-aware decision (60 seconds)

Only if a live or visibly labelled fixture forecast supports it, refresh the
plan and show:

- `defer_for_heavy_rain` for a non-critical deficit: 0% application and a
  drainage/low-spot check; or
- `reduce_for_heavy_rain` for critically dry soil: up to 25% of a calibrated
  normal split only if the farmer observes visible stress.

Say: “A high chance of rain alone is not treated as heavy rain. The app needs
the 48-hour rainfall amount too, which protects against waterlogging.”

### 5. Close with the safety boundary (45 seconds)

“This is decision support: it reads sensor and forecast evidence, explains a
recommendation, and records farmer-confirmed irrigation. Hardware actuation,
exact water volume, and field release require calibration, flow feedback, and
manual override.”

## Expected agent answer shape

For heavy rain, a good answer contains all of:

- the exact field name and current moisture with source/time;
- forecast source/fetched time and 48-hour rainfall amount;
- the decision (`defer_for_heavy_rain` or `reduce_for_heavy_rain`);
- adjustment percentage as a share of the farmer's calibrated normal amount;
- a drainage/recheck action; and
- the statement that no irrigation equipment was operated.

## Recovery playbook

| Symptom | Presenter action |
| --- | --- |
| Backend not healthy | Close the launcher, confirm port 8001 is free, then rerun `start-demo.ps1 -ResetDemo`. |
| Weather fails | State that current forecast is unavailable. Continue with sensor-only screening; do not claim weather-aware deferral. |
| No heavy rain in live forecast | Use the ordinary water-stress route, or switch only to a clearly labelled prepared fixture. |
| Simulator stopped/no new reading | Restart the Tomato `water-stress` scenario and wait one tick. |
| Agent response is vague | Ask the constrained question: “For the selected Tomato field, read the latest observations, refresh its weather, call irrigation advice, and explain the water decision.” |
| Crop-health provider unavailable | Present it as an intentional typed unavailable state; do not expose keys or call the provider from the browser. |

## Reset after rehearsal

Close Electron or press `Ctrl+C` in the launcher window. The launcher stops
only processes it started. Before another rehearsal, run the same start command
with `-ResetDemo`; it resets the demo farmer state and produces the same
repeatable Tomato scenario.

## Definition of ready

- One clean launch from `start-demo.ps1 -ResetDemo` works without manual port
  cleanup.
- The selected field is unambiguous and carries the Tomato demo source label.
- The agent gives a field-scoped, source-aware irrigation explanation.
- The live or fixture forecast is visibly labelled and matches the shown
  decision.
- The presenter can complete the offline fallback without making a weather or
  actuation claim.
