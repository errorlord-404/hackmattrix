from __future__ import annotations

from pathlib import Path

import pytest

from app.settings import ServiceSettings


@pytest.fixture()
def contract_path() -> Path:
    return Path(__file__).resolve().parents[2] / "harness" / "contracts" / "tool-registry.json"


@pytest.fixture()
def settings(contract_path: Path) -> ServiceSettings:
    return ServiceSettings(
        dev_mode=True,
        tool_contract_path=contract_path,
        max_tools=78,
    )

