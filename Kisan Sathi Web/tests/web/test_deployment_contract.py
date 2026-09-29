"""Boundary and packaging smoke tests for the standalone deployment surface."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy"


class StandaloneDeploymentContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_compose_declares_private_api_and_public_web(self) -> None:
        compose = self.read("deploy/compose.yaml")
        self.assertIn("  api:", compose)
        self.assertIn("  web:", compose)
        self.assertIn('"127.0.0.1:${API_PORT:-8000}:8000"', compose)
        self.assertIn('"${WEB_BIND:-127.0.0.1}:${WEB_PORT:-8080}:80"', compose)
        self.assertIn("condition: service_healthy", compose)

    def test_health_readiness_wiring_is_present(self) -> None:
        compose = self.read("deploy/compose.yaml")
        api_dockerfile = self.read("deploy/Dockerfile.api")
        api_main = self.read("services/api/app/main.py")
        nginx = self.read("deploy/nginx.conf")
        self.assertIn("/readyz", compose)
        self.assertIn("/healthz", api_dockerfile)
        self.assertIn('    @app.get("/readyz"', api_main)
        self.assertIn("location = /healthz", nginx)
        self.assertIn("location = /readyz", nginx)
        self.assertIn("proxy_pass http://api:8000/readyz", nginx)

    def test_provider_credentials_never_enter_web_build_or_service(self) -> None:
        compose = self.read("deploy/compose.yaml")
        web = self.read("deploy/Dockerfile.web")
        env_example = self.read("deploy/.env.example")
        web_block = compose.split("  web:", 1)[1].split("volumes:", 1)[0]
        secret_names = (
            "SARVAM_API_KEY",
            "DATA_GOV_IN_API_KEY",
            "SCRAPER_WEBHOOK_TOKEN",
            "DEVICE_INGESTION_CREDENTIALS_JSON",
        )
        for secret_name in secret_names:
            self.assertNotIn(secret_name, web)
            self.assertNotIn(secret_name, web_block)
            self.assertIn(secret_name, env_example)
        self.assertIn("VITE_API_BASE_URL", web)
        self.assertNotIn("ARG SARVAM", web)
        self.assertNotIn("ARG DATA_GOV", web)

    def test_build_inputs_do_not_back_reference_parent_runtime(self) -> None:
        for relative in ("deploy/Dockerfile.web", "deploy/Dockerfile.api", "deploy/compose.yaml"):
            text = self.read(relative).lower()
            self.assertNotIn("../backend", text)
            self.assertNotIn("/backend/", text)
            self.assertNotIn("codex", text)
            self.assertNotIn("electron", text)
        self.assertIn("context: ..", self.read("deploy/compose.yaml"))
        self.assertIn("COPY apps/web/", self.read("deploy/Dockerfile.web"))
        self.assertIn("COPY services/api/", self.read("deploy/Dockerfile.api"))

    def test_persistent_volume_contract_has_no_model_bytes(self) -> None:
        compose = self.read("deploy/compose.yaml")
        contract = self.read("deploy/volume-contracts.yaml")
        for volume in ("farm_state", "farm_uploads", "model_releases"):
            self.assertIn(volume, compose)
            self.assertIn(volume, contract)
        forbidden_suffixes = {".onnx", ".tflite", ".pt", ".pth", ".bin", ".h5", ".safetensors"}
        artifact_files = [path for path in DEPLOY.rglob("*") if path.is_file() and path.suffix.lower() in forbidden_suffixes]
        self.assertEqual([], artifact_files)

    def test_public_config_is_same_origin(self) -> None:
        env_example = self.read("deploy/.env.example")
        nginx = self.read("deploy/nginx.conf")
        self.assertIn("VITE_API_BASE_URL=/api", env_example)
        self.assertIn("location /api/", nginx)
        self.assertIn("try_files $uri $uri/ /index.html", nginx)


if __name__ == "__main__":
    unittest.main()
