from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_cv_release_is_fail_closed_until_real_approval_exists():
    record = json.loads((ROOT / "docs/APPROVED_RELEASES.json").read_text(encoding="utf-8"))
    release = record["scopes"]["release-cv"]
    assert release["approved"] is False
    assert release["activation_allowed"] is False
    vision = (ROOT / "services/api/app/services/vision_release.py").read_text(encoding="utf-8")
    assert "VisionReleaseUnavailable" in vision
