import json
from pathlib import Path

import pytest

from model_pipeline.contracts import PipelineError
from model_pipeline.evaluation import evaluate_release_candidate


def test_evaluation_command_fails_closed_for_missing_candidate(tmp_path: Path):
    with pytest.raises(PipelineError, match="existing manifest"):
        evaluate_release_candidate(tmp_path / "missing" / "manifest.json", output=tmp_path / "report.json")

