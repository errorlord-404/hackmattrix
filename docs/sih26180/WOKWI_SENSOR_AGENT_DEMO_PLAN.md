# Wokwi soil telemetry → farmer-agent demo plan

## Goal

Demonstrate a credible closed loop: mock the Wokwi soil node, ingest its
measurements using the production telemetry contract, show them in the selected
field, and have the farmer agent answer questions with freshness and source
limits intact.

## Confirmed hardware contract

The supplied Wokwi sketch uses an ESP32 + MAX3485 and polls these Modbus slave
IDs at 9600 baud: moisture `1`, temperature `2`, EC `3`, and pH `4`. It scales
moisture, temperature, and pH by ten. The NPK breakout is present in the
circuit, but the sketch neither queries nor parses it; its displayed N/P/K
values are fixed `0.0` placeholders. Therefore, phase 1 must never send or
advise from NPK values.

## Demo data path

```text
Wokwi readings / mock scenario
          ↓
mock_telemetry.py (source: device, calibration: demo-unverified)
          ↓
POST /v1/device-ingestion/observations (device auth + CRC status)
          ↓
farmer-scoped SQLite readings + device health
          ↓                         ↓
Telemetry panel          get_latest_field_observations + list_device_health
                                      ↓
                         cautious farmer-agent response
```

## Hackathon route — built-in Tomato demo simulation

The hardware bridge remains useful for later integration, but the hackathon
prototype should work without any Wokwi browser, serial cable, device token, or
physical sensor. Add a **Tomato demo mode** to the application which produces
the same `sensor_readings` shape that the real device-ingestion path produces.
It must use a distinct source such as `simulation:tomato-demo:v1`, never
`device:`. The UI should visibly show **Simulated demo data** and the agent
must say so whenever it bases an answer on these values.

### Simulator design

Run one field-scoped simulation tick every 15 seconds while the demo is active.
Persist each tick through the normal farmer-scoped reading store; then the
existing dashboard, `get_latest_field_observations`, soil-health screen and
agent tools work without a special agent-only path. Start from a deterministic
seed so that the same demo is repeatable, with optional named scenarios for a
live presentation.

```text
Tomato demo controls (scenario / water button / restart)
                         ↓
              soil-state simulator, every 15 seconds
                         ↓
  normal sensor_readings store, source=simulation:tomato-demo:v1
                         ↓
  existing field telemetry UI + agent read-only tools
                         ↓
  tomato-specific, explicitly simulated decision explanation
```

The simulated state should include `moisture`, `temperature`, `ph`, `ec`,
`nitrogen`, `phosphorus`, `potassium`, tick number, seed, last irrigated time,
and selected scenario. Each tick applies small bounded variation—not random
unbounded jumps—then clips values to valid units and ranges. A manual **Simulate
irrigation** demo control should increase moisture gradually across the next
two or three ticks and slightly dilute EC; it records only simulator state and
must never claim to activate a pump.

Suggested presentation scenarios:

| Scenario | Starting behaviour | Decision the agent should demonstrate |
| --- | --- | --- |
| `balanced` | Moisture 42%, pH 6.5, EC 0.8, adequate NPK | Continue monitoring; no unnecessary input. |
| `water-stress` | Moisture falls below 30% while temperature rises | Check recent rain/irrigation and use forecast-aware irrigation screening. |
| `nitrogen-low` | Nitrogen trends below the configured screening bound; other values stable | Flag a possible nutrient issue and request soil-test/crop-stage context before any prescription. |
| `salinity-risk` | EC climbs while moisture is moderate | Flag salt-stress risk and ask about irrigation-water quality/drainage; no amendment dose. |
| `alkaline-soil` | pH remains high and phosphorus availability is uncertain | Explain the pH concern; suggest confirmation before a treatment decision. |

The simulator's NPK values are **demo scenarios**, not readings from the
current Wokwi circuit. Unlike the phase-1 hardware bridge, Tomato demo mode may
publish NPK so the agent can demonstrate nutrient-aware reasoning—but every
such response must identify the data as simulated and screening-only.

### Implementation tasks

1. Add a feature-gated simulator service with `start`, `stop`, `restart`,
   `setScenario`, `simulateIrrigation`, and `tick` operations. It must be off
   by default and available only in local/demo builds.
2. Add a small control card to the field/demo screen: demo status, scenario
   selector, last simulated time, restart, and Simulate irrigation. Keep the
   existing live telemetry panel; add its clearly visible simulated-source
   badge rather than duplicating the panel.
3. On every tick, write all seven measurements using canonical units: `%`,
   `°C`, `pH`, `mS/cm`, and `mg/kg` for N/P/K. Use one common `observed_at`
   timestamp and `simulation:tomato-demo:v1` source.
4. Ensure simulator writes are isolated by field and cannot overwrite,
   impersonate, or downgrade a real `device:` source. Stopping the simulator
   stops new values; it does not erase the audit trail.
5. Update the agent system guidance: when the latest source begins with
   `simulation:`, call it a Tomato prototype simulation, state the relevant
   values and scenario, and frame actions as “what the app would suggest for
   this condition.” It must still check field, freshness, weather, crop stage,
   and recent irrigation before a water decision.
6. Add tests for deterministic ticks, field isolation, canonical units,
   source labelling, irrigation transition, and agent prompts for each scenario.

## Phase 1 — repeatable mock demo

1. Configure a separate local demo device ID and token, scoped to one existing
   demo field. Never expose the token in Wokwi, the client, or prompts.
2. Run the bridge in `hardware/wokwi-soil-demo/` once per scenario, increasing
   the sequence number each time.
3. Verify the API returns `accepted`, four accepted samples, and a fresh device.
4. Open the field dashboard and confirm each displayed value has `device:`
   source information and current observation time.

Acceptance: the healthy scenario appears as 42% moisture, 25.4°C, EC 0.8
mS/cm, and pH 6.5; raw zero NPK never appears as a nutrient observation.

## Phase 2 — agent-answer policy

When a user asks about watering, soil health, or sensor status, the agent must:

1. Resolve the exact field, then call `get_latest_field_observations` and
   `list_device_health`.
2. Quote the value, unit, source, and observation time. A mock source must be
   called demo/screening data, never a lab result.
3. For irrigation, also call `get_irrigation_advice` and the field-weather
   tool. Do not recommend a precise water volume.
4. Refuse a nutrient prescription when N/P/K are absent, stale, CRC-rejected,
   uncalibrated, or merely a Wokwi placeholder; request a soil test instead.
5. Ask about recent irrigation/rain before treating moisture as field truth.

Example expected answer for `low-moisture`: “The latest demo reading is 22.5%
moisture, recorded just now by the Wokwi mock node. That is a low-moisture
screening signal, so first check whether it rained or was irrigated recently;
then use the field irrigation advice with the current forecast. I cannot infer
NPK from this node because it has not provided verified nutrient readings.”

## Phase 3 — test matrix

| Scenario | Agent behaviour to prove |
| --- | --- |
| `healthy` | Report values and continue monitoring; no fertilizer prescription. |
| `low-moisture` | Flag a screening risk; check rain/recent irrigation before acting. |
| `salinity-risk` | Identify high EC as a screening concern; suggest confirmation with soil/lab context. |
| `alkaline-risk` | Identify elevated pH; do not prescribe amendments from one unverified sample. |
| stale device | State that live advice cannot rely on the reading. |
| CRC-rejected sample | State it was rejected and do not use it. |
| missing NPK | Explicitly say nutrients are unavailable, not zero. |
| Tomato simulated NPK | State that NPK is simulated, use it only as a screening scenario, and do not present it as Wokwi hardware data. |
| simulated irrigation | Show moisture rising over later ticks and explain that no pump was activated. |

## Phase 4 — actual hardware follow-up

1. Replace bridge-generated values with a serial/Wi-Fi gateway that submits the
   same envelope and preserves the actual `observed_at`, device ID, sequence,
   RSSI and CRC result.
2. Add NPK parsing only after documenting the sensor’s actual Modbus register
   map, units, calibration procedure, and range checks.
3. Calibrate each probe against field/lab reference measurements, record a new
   calibration revision, and validate trends before upgrading any advice beyond
   screening guidance.
