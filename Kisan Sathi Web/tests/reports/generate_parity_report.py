from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = {
    "MIG-01": ["standalone-boundary"],
    "MIG-02": ["standalone-boundary"],
    "WEB-01": ["api-tests"],
    "WEB-02": ["deployment-contract"],
    "WEB-03": ["api-tests"],
    "WEB-04": ["harness-tests"],
    "WEB-05": ["harness-tests"],
    "WEB-06": ["harness-tests"],
    "WEB-07": ["load-failure-tests"],
    "WEB-08": ["contract-tests"],
    "WEB-09": ["load-failure-tests"],
    "WEB-10": ["frontend-tests", "frontend-build"],
    "CVWEB-01": ["cv-approval", "model-catalog", "browser-vision-tests"],
    "CVWEB-02": ["cv-approval", "model-catalog", "browser-vision-tests", "api-tests"],
    "WEBVER-01": ["contract-tests", "browser-matrix", "browser-vision-tests", "frontend-tests"],
    "WEBVER-02": ["deployment-contract", "browser-matrix", "standalone-boundary", "cv-approval"],
}


def render(payload: dict) -> str:
    result_by_id = {item["id"]: item for item in payload.get("results", [])}
    lines = [
        "# Phase 7 parity report",
        "",
        "Generated exclusively from `tests/results/gate-results.json`.",
        "",
        f"- Overall machine status: **{payload.get('status', 'fail')}**",
        f"- Release ready: **{str(payload.get('release_ready', False)).lower()}**",
        f"- Approval record digest: `{payload.get('approval_record_digest', '')}`",
        "",
        "| Requirement | Evidence IDs | Status |",
        "|---|---|---|",
    ]
    for requirement, evidence_ids in REQUIREMENTS.items():
        statuses = [result_by_id.get(item, {}).get("status", "missing") for item in evidence_ids]
        status = "pass" if statuses and all(value == "pass" for value in statuses) else "fail"
        lines.append(f"| {requirement} | {', '.join(evidence_ids)} | {status} |")
    lines.extend(["", "A failing or missing machine result cannot be overridden by this report.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/PARITY_REPORT.md")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--release-evidence", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.results.read_text(encoding="utf-8"))
    content = render(payload)
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != content:
            print("parity report: FAIL: output is stale or missing")
            return 1
        print("parity report: PASS")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"parity report: wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
