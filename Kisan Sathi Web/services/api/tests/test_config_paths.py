from pathlib import Path

from app.core.config import standalone_root


def test_standalone_root_contains_runtime_models_and_docs():
    root = standalone_root()
    assert (root / "models").is_dir()
    assert (root / "docs").is_dir()
    assert Path(root).name == "Kisan Sathi Web"
