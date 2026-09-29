"""Check literal frontend adapter paths against the FastAPI OpenAPI surface."""

from __future__ import annotations

import re
from pathlib import Path

from app.main import app


ROOT = Path(__file__).resolve().parents[1]
ADAPTERS = (ROOT / "src/api/farmStateApi.js", ROOT / "src/api/referenceApi.js")


def shape(path: str) -> str:
    path = re.sub(r"\$\{[^}]+\}", "{}", path)
    path = re.sub(r"\{[^}]+\}", "{}", path)
    return path.rstrip("/") or "/"


def main() -> int:
    openapi_shapes = {shape(path) for path in app.openapi()["paths"]}
    frontend_paths: set[str] = set()
    literal_pattern = re.compile(r"[\"'`]((?:\$\{[^}]+\}|[^\"'`])*)[\"'`]")
    for adapter in ADAPTERS:
        text = adapter.read_text(encoding="utf-8")
        for match in literal_pattern.finditer(text):
            raw = match.group(1)
            if not raw.startswith(("/v1", "/health", "/crops", "/market", "/msp", "/gov-", "/machinery-", "/marketplace")):
                continue
            raw = re.sub(r"\$\{queryString\(.*?\)\}", "", raw)
            raw = re.sub(r"\$\{[^}]+\}", "{}", raw).split("?")[0]
            frontend_paths.add(shape(raw))
    missing = sorted(path for path in frontend_paths if path not in openapi_shapes)
    print(f"frontend adapter path shapes: {len(frontend_paths)}")
    print(f"OpenAPI path shapes: {len(openapi_shapes)}")
    if missing:
        print("missing:")
        print("\n".join(missing))
        return 1
    print("all literal frontend adapter paths have an OpenAPI route shape")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
