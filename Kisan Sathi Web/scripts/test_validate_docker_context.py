from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.validate_docker_context import validate_dockerignore


def test_standalone_docker_context_excludes_quarantined_models():
    report = validate_dockerignore(Path(__file__).resolve().parents[1] / ".dockerignore")
    assert report["status"] == "valid_docker_context_exclusions"
