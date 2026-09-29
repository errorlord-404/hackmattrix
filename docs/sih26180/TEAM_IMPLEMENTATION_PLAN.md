# KisanSathi SIH26180 — six-person field-deployment plan

**Version:** 1.0

**Date:** 6 September 2026

**Scope:** the hardware shown in the supplied soil-health monitor diagram, the supplied Wokwi project link, and the current KisanSathi repository.
**Decision:** build a safe, demonstrable *soil-observation-to-advice* vertical slice first. It must read the two RS485 probes, show trustworthy live/stale state in the app, preserve history, and make an advisory irrigation recommendation. It must **not** autonomously switch a mains pump in the SIH MVP.

This is a delivery plan, not evidence that the supplied Wokwi project or hardware has passed a real-device test. The Wokwi project could not be retrieved from its public link during this review, and its project source is not versioned in this repository. The circuit image is therefore a reference design to be verified at the bench.

## 1. What is already built versus what this team must add

| Area | Present in repository | Gap to close | Owner |
|---|---|---|---|
| Farmer application | React/Vite pages for fields, maps, soil health, dashboard, weather and AI; Hindi/English scaffolding | Device onboarding, live/stale telemetry states, calibration and offline/error UX | Prachi, Harshwardhan |
| Farm API | `backend/app/farm_state/` stores fields, soil tests, sensor devices and readings; `POST /v1/sensor-readings` accepts manually confirmed readings | Device identity, authenticated ingestion, ordering/idempotency, calibration metadata, raw Modbus evidence and telemetry health | Aman |
| Agent / harness | `agent/src/kisansathi_agent/` exposes `record_sensor_reading`; `desktop/codex-harness.cjs` starts local `codex app-server` with a KisanSathi MCP plugin | Safe read-only device status/advice tools, contract integration and evaluation; no direct actuation from language model | Pranav |
| Hardware | Circuit reference: ESP32-S3, two RS485 probes, a MAX3485-labelled module and a 12 V-to-5 V buck | Verified wiring, real Modbus reads, stable power, enclosure and field calibration | Varuna, Anwaar |
| ML/DL | Diagnosis path and product research exist, but no fielded model artifact/registry or on-device inference runtime | One crop/region baseline, model card, confidence/fallback and evaluation data loop | Pranav |

**Important repository finding:** there is no checked-in firmware, PlatformIO/Arduino project, Wokwi `diagram.json`, Wokwi configuration or actual sensor connector contract. Anwaar must export the Wokwi project into source control before feature work starts. The current manual API and MCP write tool are not a safe substitute for an IoT ingress endpoint.

## 2. P0 hardware corrections — resolve before connecting a field installation

The image contains one likely electrical mismatch: it labels the transceiver **MAX3485** while placing it on the shared 5 V rail. A genuine MAX3485 is a 3.3 V device. Do not apply 5 V to a module that is actually MAX3485-based. First inspect the module silkscreen, product link and data sheet; photograph the board and record the result in the hardware log. If it is a 5 V MAX485-style module instead, its `RO` output must not be connected directly to the ESP32-S3 without proving safe logic levels. Prefer a known 3.3 V RS485 module or an isolated field-rated transceiver for the final unit. [MAX3485 product documentation](https://www.analog.com/en/products/max3485.html)

The two probes are RS485/Modbus devices, not interchangeable laboratory instruments. The SEN0604 reports moisture, temperature, pH and EC and accepts a wide supply range; its published wiring identifies `VCC`, `GND`, `485-A` and `485-B`. [SEN0604 documentation](https://wiki.dfrobot.com/sen0604/) The SEN0605 is also 5–30 V/RS485 but its vendor explicitly describes N/P/K output as reference data rather than professional-grade accuracy. Treat NPK values as a trend/screening signal until compared against laboratory or Soil Health Card data. [SEN0605 documentation](https://wiki.dfrobot.com/sen0605/)

### P0 checklist

1. **Freeze the actual BOM.** Record purchase links, board photographs, exact sensor labels, cable markings, supply ratings, wire gauge and firmware commit. Do not infer a sensor wire by colour: the supplied image and vendor documentation do not use identical colour labels. Wire by the printed terminal/function label (`VCC`, `GND`, `A`, `B`).
2. **Separate power domains.** Use 12 V at the input fuse; use a buck output only after measuring it under load. Feed a compatible 5 V/VIN pin on the ESP32-S3 development board, never its 3.3 V pin. Feed a genuine MAX3485 from ESP32 3.3 V. Feed each sensor only within its verified rating. Common signal reference/grounding must follow the selected transceiver module's design; do not assume that drawing a shared ground alone solves long-cable field grounding.
3. **Address the probes one at a time.** Both probe families may ship at Modbus address `0x01`. With only one sensor connected, query it, change and read back its assigned address; then connect the other. The target allocation is SEN0604 `0x01`, SEN0605 `0x02`, but only after a documented read-back. The SEN0604's Modbus protocol is 9600, 8N1 by default. [SEN0604 Modbus protocol](https://wiki.dfrobot.com/sen0604/docs/20297) The SEN0605 documentation exposes configurable address and baud settings. [SEN0605 reference/API](https://wiki.dfrobot.com/sen0605/docs/21024)
4. **Treat the bus as half duplex.** On the labelled ESP32-S3 wiring, `GPIO17 → DI`, `GPIO18 ← RO`, `GPIO16 → DE`, `GPIO4 → /RE`. Idle/read state is `DE=LOW`, `/RE=LOW`; transmit state is `/RE=HIGH`, `DE=HIGH`; wait for UART transmission completion before returning to read. Add boot-state pull resistors so a reset cannot hold the field bus driven.
5. **Build the field layer deliberately.** Use twisted pair for A/B, strain relief and a weatherproof enclosure. Add termination only at the physical ends of a longer bus, then validate it with the actual cable; include transient/ESD and surge/lightning protection before outdoor deployment. Breadboards are acceptable only for a supervised bench test.
6. **Validate against ground truth.** At a recorded depth and placement, compare pH/EC/moisture/NPK readings with a known reference or laboratory result, record soil type and soil moisture condition, and publish a calibration/uncertainty note. The SEN0605 supplier directs multiple measurements and averaging and specifies an insertion method; use it as the starting procedure, not as a final calibration. [SEN0605 installation guidance](https://wiki.dfrobot.com/sen0605/docs/21024)
7. **No unsupervised pump demo.** Any future irrigation controller must be an isolated, rated low-voltage control system with physical manual override, stop/timeout, flow feedback and a local fail-safe. The first demonstrator emits an advice/task only.

## 3. Approved wiring and communication contract

This table is the proposed target after P0 verification; it supersedes no manufacturer data sheet.

| Connection | Target | Acceptance check |
|---|---|---|
| 12 V adapter | input fuse → buck converter | Measured polarity and loaded voltage recorded |
| Buck 5 V rail | ESP32-S3 board 5 V/VIN; sensors only if verified compatible | ESP32 board regulates to 3.3 V; no 5 V on its 3.3 V rail |
| ESP32 3.3 V rail | genuine MAX3485 VCC | Measured 3.0–3.6 V; transceiver part confirmed |
| ESP32 GPIO17 | RS485 `DI` | UART transmit log passes |
| ESP32 GPIO18 | RS485 `RO` | UART receive log passes and voltage safe for ESP32 |
| ESP32 GPIO16 / GPIO4 | `DE` / active-low `/RE` | Read and transmit state test passes |
| RS485 `A`, `B` | both sensors in daisy chain | Correct labels, no polarity guessed from colour; individual Modbus reads pass |
| Sensor device IDs | `soil-node-<serial>`, probe `sen0604-01`, `sen0605-02` | Device registration, firmware version and Modbus address stored |

The ESP32-S3 has flexible UART pin routing, but the firmware must set the selected pins explicitly and reserve boot/programming pins. [Espressif UART documentation](https://docs.espressif.com/projects/esp-idf/en/release-v5.4/esp32s3/api-reference/peripherals/uart.html)

### Firmware behaviour

The soil node has exactly these states:

`BOOT → SELF_TEST → POLL_SEN0604 → POLL_SEN0605 → VALIDATE → QUEUE → UPLOAD → SLEEP/RETRY`

- Poll at a configurable, conservative interval (start at 15 minutes; never claim that faster polling improves soil truth).
- Preserve raw Modbus response metadata, CRC result, probe address, firmware version, boot ID and monotonically increasing sequence number.
- Reject values outside sensor-defined ranges, tag `invalid`, and upload a health event rather than silently creating an agronomic reading.
- Queue unsent observations locally with bounded storage; retry using exponential backoff. Never manufacture timestamps after loss of time synchronization.
- Upload only through a dedicated device-ingestion service. It must not call the farmer-facing MCP write tool.
- Wokwi is useful for firmware state/UART/Wi-Fi message flow, but it does not prove the physical RS485 probes, cables, power noise, waterproofing or calibration. Wokwi documents ESP32-S3 support and HTTP/MQTT Wi-Fi simulation; export its `diagram.json`, sketch and `wokwi.toml` to the repository. [Wokwi ESP32 guide](https://docs.wokwi.com/guides/esp32) · [Wokwi project configuration](https://docs.wokwi.com/vscode/project-config)

## 4. System integration contract

### Device telemetry envelope (new, proposed)

`POST /v1/device-ingestion/observations` is a planned endpoint. It is deliberately separate from the existing `/v1/sensor-readings` farmer/agent route.

```json
{
  "device_id": "soil-node-a17f",
  "field_id": "uuid",
  "boot_id": "uuid",
  "sequence": 42,
  "observed_at": "2026-09-06T10:20:30Z",
  "firmware_version": "0.1.0",
  "samples": [
    {"probe": "sen0604-01", "measurement": "moisture", "value": 31.4, "unit": "%", "modbus_address": 1, "crc_ok": true},
    {"probe": "sen0605-02", "measurement": "nitrogen", "value": 55, "unit": "mg/kg", "modbus_address": 2, "crc_ok": true}
  ],
  "transport": {"rssi_dbm": -67, "queued_seconds": 0}
}
```

Implementation rules:

- Authenticate every device with a provisioned credential stored outside git; scope it to its farm/field and rotate/revoke it.
- Make `(device_id, boot_id, sequence)` idempotent; store both valid data and rejected/error events with a reason.
- Keep source, observed time, received time, calibration revision, depth/placement, sensor serial and data-quality status. Do not overwrite a raw observation with a later recommendation.
- The backend calculates advice. The agent only asks the domain API for a cited status/recommendation and explains it in the farmer's language.
- A stale/missing sensor must render as **unknown**, not “healthy” or “no irrigation needed.”

### Required product path for the SIH demo

`Probe → ESP32/RS485 → signed telemetry → API validation/history → dashboard status → irrigation advisory/task → Codex/MCP explanation in local language`

For the first demo, advice is based on a documented crop-stage and moisture rule plus weather provenance; it does not advertise autonomous optimization. Water actuation remains a later safety-gated module.

## 5. Team ownership and non-overlapping deliverables

| Person | Primary ownership | Must deliver | Explicit boundary |
|---|---|---|---|
| **Varuna** | Electronics and field hardware lead | Corrected schematic/BOM, power budget, enclosure and connector plan, bench safety checklist, calibration protocol and evidence log | Does not implement app/API logic; signs off only after P0 checks |
| **Anwaar** | ESP32, RS485 and Wokwi firmware lead | `firmware/soil-node/` with exported Wokwi project, Modbus address/read utility, polling state machine, telemetry queue, serial test log and flashing guide | Does not change API schema without Aman; no pump relay code in MVP |
| **Prachi** | Farmer-facing live-data frontend lead | Device status card; current/stale/error telemetry UX; field soil screen; accessible Hindi/English labels; component tests | Consumes the agreed API only; no embedded hardware rules in React |
| **Harshwardhan** | Frontend onboarding and demo-flow lead | Field-to-device onboarding, calibration/placement capture, historical trend and data-age display, graceful offline/error states, end-to-end demo checklist | Does not create an alternate backend or duplicate Prachi's status components |
| **Aman** | Backend functions and tools lead | Device enrollment/credential flow, ingestion endpoint, unit/schema validation, idempotent persistence, device health/read APIs, tests and OpenAPI contract | Does not expose credentials to the MCP agent or grant agent physical control |
| **Pranav** | Codex-fork integration and ML/DL lead | Existing MCP/plugin + `codex app-server` integration test, safe read-only status/advice tools, model/dataset decision record, one fieldable crop-health baseline with model card/evaluation, multilingual answer wiring | Keeps farm-domain logic in FastAPI/services. Do not start the stale Rust-handler plan unless a concrete upstream Codex extension requirement appears |

### File ownership map

| Owner | Expected paths |
|---|---|
| Varuna | `hardware/soil-node/SCHEMATIC.md`, `BOM.csv`, `CALIBRATION.md`, `TEST_LOG.md` |
| Anwaar | `firmware/soil-node/**` including `wokwi/diagram.json`, `wokwi.toml`, source and `README.md` |
| Prachi | `src/components/features/sensors/**`, soil/dashboard components and tests |
| Harshwardhan | `src/pages/DeviceOnboarding.jsx`, `src/components/fields/**`, user-flow tests |
| Aman | `backend/app/routers/device_ingestion.py`, schemas/models/services/migrations/tests under an agreed `device_ingestion` scope |
| Pranav | `agent/src/kisansathi_agent/**`, `desktop/**` only as necessary, `ml/**`, model cards/evaluation and integration tests |

All owners may update their own documentation. Shared contracts live in `docs/sih26180/`; schema changes require Aman + the affected producer/consumer to approve one pull request before implementation.

## 6. Six-week execution sequence

| Week | Integration objective | Owner outcomes | Gate |
|---|---|---|---|
| **0 (days 1–2)** | Lock interfaces and correct the circuit | Varuna verifies BOM/power; Anwaar exports Wokwi; Aman publishes telemetry schema; Prachi/Harshwardhan provide UI states; Pranav pins demo crop/model decision | P0 checklist accepted; no questionable 5 V transceiver wiring |
| **1** | Obtain stable, individual probe reads | Varuna/Anwaar show repeatable serial logs for both addresses; Aman supplies mocked ingestion; frontend renders mocks; Pranav defines advisory wording | 20 consecutive valid polls per probe on bench |
| **2** | Persist real telemetry safely | Firmware posts/retries; Aman implements authentication, idempotency and health; UI consumes staging data | Duplicate packet causes no duplicate reading; unplugged probe visibly becomes fault/stale |
| **3** | Demonstrate farmer flow | Prachi/Harshwardhan complete setup → field → current/stale history views; Pranav connects read-only agent explanation and model baseline | A farmer can identify field, data age, source and uncertainty without chat |
| **4** | Validate decisions and resilience | Varuna runs calibration checks; Aman/Anwaar test Wi-Fi loss and reboot; Pranav runs model evaluation/fallback; frontend tests error paths | Offline backlog drains once, invalid CRC never becomes advice |
| **5** | SIH rehearsal | Entire team runs one scripted field-like demo, records evidence video and limitations | End-to-end path is repeatable; no unvalidated accuracy or autonomous-pump claim |

## 7. Definition of done and demo evidence

The vertical slice is done only when all are true:

- The exact board and probes used are documented, addresses are unique and both survive power-cycle reads.
- The real device uploads one signed, idempotent observation and a planned outage/retry test has evidence.
- The dashboard labels source, observation time, freshness, unit, field, known calibration status and an error state.
- The agent can report the same API-backed status in the selected language and says “unknown” for a stale or failed probe.
- The irrigation output is an explainable recommendation/task, never a language-model-issued relay action.
- Vision output is either a validated model result with confidence/fallback or explicitly “inconclusive”; it never invents a disease label.
- A short evidence pack contains wiring photos, serial output, API test, frontend test, agent transcript, calibration comparison and an honest limitation slide.

## 8. Risks that should stay visible to judges

1. **Sensor quality:** low-cost NPK values cannot be presented as laboratory soil tests. Compare against a reference and state the measurement's role.
2. **Field robustness:** Wokwi validates program flow, not cable surge/lightning, water ingress, sensor drift or RF conditions.
3. **Decision safety:** do not turn a moisture threshold into an automatic irrigation decision. Crop stage, root-zone water balance, rainfall amount/timing, pump/flow feedback and a manual stop are prerequisites.
4. **Disease AI:** a high validation accuracy on curated images is not field performance. Record local photos, target crop/region, confidence threshold and escalation path.
5. **Codex boundary:** the assistant may explain and create reviewable tasks; services/controllers retain authority for calculations and any future actuation.

## 9. Immediate next actions

1. Varuna photographs and verifies the actual RS485 module before it is powered; fix the 5 V/3.3 V question.
2. Anwaar exports the Wokwi project and creates the `firmware/soil-node/` skeleton with a single-probe Modbus read test.
3. Aman writes the OpenAPI request/response contract and a fake-device integration test before firmware posts to production.
4. Prachi and Harshwardhan build against the mock telemetry contract, including stale/fault states.
5. Pranav adds an agent read tool over the canonical device-status API and produces a one-crop model/data decision record.

## Source notes

- [MAX3485, Analog Devices](https://www.analog.com/en/products/max3485.html) — 3.3 V RS485/RS422 transceiver specification.
- [DFRobot SEN0604](https://wiki.dfrobot.com/sen0604/) and [Modbus protocol](https://wiki.dfrobot.com/sen0604/docs/20297) — four-in-one probe and default communication reference.
- [DFRobot SEN0605](https://wiki.dfrobot.com/sen0605/) and [reference/API](https://wiki.dfrobot.com/sen0605/docs/21024) — NPK probe limitations, configuration and installation notes.
- [Espressif ESP32-S3 UART](https://docs.espressif.com/projects/esp-idf/en/release-v5.4/esp32s3/api-reference/peripherals/uart.html) — configurable UART routing.
- [Wokwi ESP32](https://docs.wokwi.com/guides/esp32) and [project configuration](https://docs.wokwi.com/vscode/project-config) — simulation capabilities and source files to export.
