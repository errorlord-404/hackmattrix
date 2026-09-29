import unittest
from pathlib import Path
from unittest.mock import patch

from orchestration.hierarchical_inference import run_hierarchical_inference


class HierarchicalInferenceTest(unittest.TestCase):
    @patch("orchestration.hierarchical_inference._checkpoint_candidates")
    def test_does_not_call_specialist_until_crop_is_confirmed(self, candidates):
        candidates.return_value = [{"label": "tomato", "score": 0.78}, {"label": "maize", "score": 0.72}]
        result = run_hierarchical_inference(Path("photo.jpg"), Path("router.pt"), {"tomato": Path("tomato.pt")})
        self.assertEqual(result["status"], "needs_expert_review")
        self.assertEqual(candidates.call_count, 1)

    @patch("orchestration.hierarchical_inference._checkpoint_candidates")
    def test_unknown_confirmed_crop_fails_closed(self, candidates):
        candidates.return_value = [{"label": "tomato", "score": 0.95}]
        result = run_hierarchical_inference(Path("photo.jpg"), Path("router.pt"), {"tomato": Path("tomato.pt")}, confirmed_crop="rice")
        self.assertEqual(result["status"], "unsupported_crop")
        self.assertEqual(result["disease_candidates"], [])


if __name__ == "__main__":
    unittest.main()
