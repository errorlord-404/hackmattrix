# Wokwi soil-sensor mock demo

`mock_telemetry.py` simulates the four readings which the supplied Wokwi ESP32
firmware really requests over Modbus:

| Wokwi slave ID | KisanSathi measurement | Unit |
| --- | --- | --- |
| 1 | `moisture` | `%` |
| 2 | `temperature` | `°C` |
| 3 | `ec` | `mS/cm` |
| 4 | `ph` | `pH` |

The mock sends the authenticated `POST /v1/device-ingestion/observations`
contract. The backend retains the source (`device:...`), observation time,
device health and calibration label, so both the dashboard and farmer agent
read the mock through their normal, farmer-scoped APIs.

## Run a safe preview

```powershell
python hardware/wokwi-soil-demo/mock_telemetry.py --token placeholder --field-id field-id --scenario healthy --dry-run
```

## Send a demo packet

First provision `soil-node-wokwi-demo` for an existing field in
`DEVICE_INGESTION_CREDENTIALS_JSON`. Use a local demo-only token; never put a
real token in Wokwi code, source control, screenshots, or prompts.

```powershell
python hardware/wokwi-soil-demo/mock_telemetry.py `
  --token <demo-device-token> `
  --field-id <provisioned-field-id> `
  --scenario low-moisture `
  --sequence 1
```

For a new reading, increment `--sequence`; the API intentionally treats a
repeated device/boot/sequence tuple as an idempotent replay.

Available scenarios: `healthy`, `low-moisture`, `salinity-risk`, and
`alkaline-risk`. These are explicitly mock, screening-only data—not lab soil
test values or a fertilizer prescription.

## NPK limitation

The Wokwi circuit includes an NPK breakout, but its current `sketch.ino` does
not read that sensor. It prints `N: 0.0`, `P: 0.0`, and `K: 0.0` as fixed
placeholders. This bridge deliberately does not send NPK values, so the agent
must call them unavailable rather than interpreting zero as an actual reading.
