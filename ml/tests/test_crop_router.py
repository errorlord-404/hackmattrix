import unittest

from orchestration.crop_router import CropCandidate, select_specialist


class CropRouterTest(unittest.TestCase):
    def setUp(self):
        self.specialists = {"tomato": "tomato-health-v0.1", "rice": "rice-health-v0.1"}

    def test_routes_confident_supported_crop(self):
        result = select_specialist([CropCandidate("tomato", 0.91), CropCandidate("rice", 0.04)], self.specialists)
        self.assertEqual(result.status, "routed")
        self.assertEqual(result.specialist_id, "tomato-health-v0.1")

    def test_ambiguous_crop_requires_confirmation(self):
        result = select_specialist([CropCandidate("tomato", 0.78), CropCandidate("rice", 0.72)], self.specialists)
        self.assertEqual(result.status, "needs_crop_confirmation")
        self.assertTrue(result.requires_farmer_confirmation)

    def test_confirmed_unsupported_crop_does_not_fallback(self):
        result = select_specialist([], self.specialists, confirmed_crop="wheat")
        self.assertEqual(result.status, "unsupported_crop")
        self.assertIsNone(result.specialist_id)


if __name__ == "__main__":
    unittest.main()
