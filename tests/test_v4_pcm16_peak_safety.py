import unittest

import numpy as np

from app.v4_audio_processing import pcm16_safe_pair


class Pcm16PeakSafetyTests(unittest.TestCase):
    def test_overrange_pair_gets_one_shared_gain_and_stays_below_full_scale(self):
        original = np.array([1.0, -0.8, 0.25], dtype=np.float32)
        marked = np.array([1.0001, -0.79, 0.26], dtype=np.float32)

        safe_original, safe_marked, gain = pcm16_safe_pair(original, marked)

        self.assertLess(gain, 1.0)
        self.assertAlmostEqual(float(np.max(np.abs(safe_marked))), 1 - 2 / 32768, places=7)
        self.assertLess(float(np.max(np.abs(safe_original))), 1.0)
        np.testing.assert_allclose(safe_original, original * gain)
        np.testing.assert_allclose(safe_marked, marked * gain)

    def test_in_range_pair_is_unchanged(self):
        original = np.array([0.7, -0.4], dtype=np.float32)
        marked = np.array([0.71, -0.41], dtype=np.float32)

        safe_original, safe_marked, gain = pcm16_safe_pair(original, marked)

        self.assertEqual(gain, 1.0)
        np.testing.assert_array_equal(safe_original, original)
        np.testing.assert_array_equal(safe_marked, marked)


if __name__ == "__main__":
    unittest.main()
