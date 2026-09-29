"""Static and runtime-safe deployment contract checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class DeploymentContractError(ValueError):
    """Raised when the standalone deployment topology is unsafe or incomplete."""


def load_compose(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise DeploymentContractError(f"compose file is missing: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict) or not isinstance(payload.get("services"), dict):
        raise DeploymentContractError("compose file must contain a services object")
    return payload


def validate_compose(path: Path) -> dict[str, Any]:
    payload = load_compose(path)
    services = payload["services"]
    required = {"api", "harness", "web"}
    missing = sorted(required - set(services))
    if missing:
        raise DeploymentContractError(f"required services are missing: {', '.join(missing)}")
    for name in required:
        service = services[name]
        if not isinstance(service, dict):
            raise DeploymentContractError(f"service {name} must be an object")
        build = service.get("build")
        if not isinstance(build, dict) or build.get("context") != "..":
            raise DeploymentContractError(f"service {name} must build from the standalone root")
        if "healthcheck" not in service:
            raise DeploymentContractError(f"service {name} must define a healthcheck")
    web_depends = services["web"].get("depends_on", {})
    if not isinstance(web_depends, dict) or set(web_depends) < {"api", "harness"}:
        raise DeploymentContractError("web must be health-gated on api and harness")
    if services["web"].get("depends_on", {}).get("api", {}).get("condition") != "service_healthy":
        raise DeploymentContractError("web/api dependency must use service_healthy")
    if services["web"].get("depends_on", {}).get("harness", {}).get("condition") != "service_healthy":
        raise DeploymentContractError("web/harness dependency must use service_healthy")
    api_text = path.parent.joinpath("Dockerfile.api").read_text(encoding="utf-8")
    harness_text = path.parent.joinpath("Dockerfile.harness").read_text(encoding="utf-8")
    if "models/candidates" not in path.parent.parent.joinpath(".dockerignore").read_text(encoding="utf-8"):
        raise DeploymentContractError("Docker context does not exclude quarantined candidates")
    if "USER kisansathi" not in api_text or "USER kisansathi" not in harness_text:
        raise DeploymentContractError("server images must run as the least-privilege user")
    nginx = path.parent.joinpath("nginx.conf").read_text(encoding="utf-8")
    for required_text in ("location /api/", "location /harness/", "proxy_buffering off", "text/event-stream"):
        if required_text not in nginx:
            raise DeploymentContractError(f"proxy contract is missing: {required_text}")
    return payload
