"""Send clearly labelled Wokwi soil-node demo readings to KisanSathi.

This is a local demo bridge, not ESP32 firmware.  It uses exactly the
device-ingestion envelope accepted by the backend, so the UI and agent see
mocked readings through the same read path used by a real provisioned node.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCENARIOS = {
    "healthy": {
        "moisture": (42.0, "%"),
        "temperature": (25.4, "°C"),
        "ec": (0.8, "mS/cm"),
        "ph": (6.5, "pH"),
    },
    "low-moisture": {
        "moisture": (22.5, "%"),
        "temperature": (30.2, "°C"),
        "ec": (0.9, "mS/cm"),
        "ph": (6.6, "pH"),
    },
    "salinity-risk": {
        "moisture": (35.1, "%"),
        "temperature": (27.8, "°C"),
        "ec": (3.1, "mS/cm"),
        "ph": (7.1, "pH"),
    },
    "alkaline-risk": {
        "moisture": (38.7, "%"),
        "temperature": (26.4, "°C"),
        "ec": (1.0, "mS/cm"),
        "ph": (8.4, "pH"),
    },
}


def packet(args: argparse.Namespace) -> dict:
    readings = SCENARIOS[args.scenario]
    # These IDs match the slave IDs the supplied Wokwi sketch reads:
    # 1=moisture, 2=temperature, 3=EC, 4=pH.
    probes = (
        ("sen0604-moisture", "moisture", 1),
        ("sen0605-temperature", "temperature", 2),
        ("soil-ec", "ec", 3),
        ("soil-ph", "ph", 4),
    )
    return {
        "device_id": args.device_id,
        "field_id": args.field_id,
        "boot_id": args.boot_id,
        "sequence": args.sequence,
        "observed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "firmware_version": "wokwi-mock-0.1.0",
        "samples": [
            {
                "probe_id": probe_id,
                "measurement": measurement,
                "value": readings[measurement][0],
                "unit": readings[measurement][1],
                "modbus_address": address,
                "crc_ok": True,
                "calibration_revision": "demo-unverified",
            }
            for probe_id, measurement, address in probes
        ],
        "transport": {"rssi_dbm": -62, "queued_seconds": 0},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8001", help="KisanSathi backend base URL")
    parser.add_argument("--token", required=True, help="Provisioned device bearer token")
    parser.add_argument("--field-id", required=True, help="Existing farmer field ID provisioned for this device")
    parser.add_argument("--device-id", default="soil-node-wokwi-demo")
    parser.add_argument("--boot-id", default="wokwi-demo-boot-001")
    parser.add_argument("--sequence", type=int, default=1, help="Increase for each distinct packet")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="healthy")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without sending it")
    args = parser.parse_args()

    payload = packet(args)
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    request = Request(
        f"{args.api_url.rstrip('/')}/v1/device-ingestion/observations",
        data=body,
        headers={"Authorization": f"Bearer {args.token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            print(response.read().decode("utf-8"))
    except HTTPError as exc:
        print(exc.read().decode("utf-8"), file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Could not reach backend: {exc.reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
