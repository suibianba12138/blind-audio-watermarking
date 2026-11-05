from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

import numpy as np

from app.audio_io import AudioData
from app.v4_audio_processing import (
    add_noise,
    analyze_pair,
    fixed_crop,
    parse_payload,
    prepare_audio,
    process_channel,
)


def probe(seconds=3, sample_rate=48000, seed=73):
    rng = np.random.default_rng(seed)
    return AudioData((0.12 * rng.standard_normal(seconds * sample_rate)).astype(np.float64), sample_rate)


class AudioProcessingTests(unittest.TestCase):
    def test_parse_payload_enforces_backend_capacities(self):
        self.assertEqual(parse_payload("Advanced Neural", "0xD3916B24E8"), bytes.fromhex("D3916B24E8"))
        self.assertEqual(parse_payload("Classic DSP", "123"), 123)
        self.assertEqual(parse_payload("Classic DSP", "0x7B"), 123)
        with self.assertRaises(ValueError):
            parse_payload("Advanced Neural", "1234")
        with self.assertRaises(ValueError):
            parse_payload("Classic DSP", "256")


    def test_prepare_audio_resamples_and_produces_exact_backend_length(self):
        source = probe(seconds=2, sample_rate=16000)
        result = prepare_audio(source, target_sample_rate=44100, duration_seconds=12)
        self.assertEqual(result.sample_rate, 44100)
        self.assertEqual(result.samples.shape, (44100 * 12,))
        self.assertTrue(np.all(np.isfinite(result.samples)))


    def test_noise_is_reproducible_and_matches_requested_snr(self):
        source = probe()
        first = add_noise(source, snr_db=20, seed=2026)
        second = add_noise(source, snr_db=20, seed=2026)
        np.testing.assert_array_equal(first.samples, second.samples)
        err = first.samples - source.samples
        measured = 10 * np.log10(np.mean(source.samples ** 2) / np.mean(err ** 2))
        self.assertAlmostEqual(measured, 20, delta=1e-5)


    def test_fixed_crop_uses_explicit_start_and_duration(self):
        source = AudioData(np.arange(48000 * 5, dtype=np.float64), 48000)
        crop = fixed_crop(source, start_seconds=1.25, duration_seconds=2.0)
        self.assertEqual(crop.samples.size, 96000)
        np.testing.assert_array_equal(crop.samples, source.samples[60000:156000])


    def test_analysis_aligns_codec_offset_before_snr_and_lsd(self):
        source = probe(seconds=4)
        offset = np.pad(source.samples, (int(0.08 * source.sample_rate), 0))
        result = analyze_pair(source, AudioData(offset, source.sample_rate), max_offset_seconds=0.2)
        self.assertIs(result["metrics_available"], True)
        self.assertLessEqual(abs(result["lag_seconds"] - 0.08), 1 / 2000)
        self.assertGreater(result["snr_db"], 100)
        self.assertGreaterEqual(result["compared_seconds"], 3.8)


    def test_analysis_refuses_unrelated_signals_instead_of_reporting_snr(self):
        source = probe(seconds=4, seed=71)
        unrelated = probe(seconds=4, seed=72)
        result = analyze_pair(source, unrelated, max_offset_seconds=0.2, min_alignment_score=0.15)
        self.assertIs(result["metrics_available"], False)
        self.assertIsNone(result["snr_db"])
        self.assertIsNone(result["lsd_db"])

    def test_analysis_uses_real_overlap_without_backend_zero_padding(self):
        source = probe(seconds=4)
        shorter = AudioData(source.samples[: 2 * source.sample_rate], source.sample_rate)
        result = analyze_pair(source, shorter, max_offset_seconds=0.2)
        self.assertTrue(result["metrics_available"])
        self.assertAlmostEqual(result["compared_seconds"], 2.0, places=2)
        self.assertGreater(result["snr_db"], 100)

    def test_aac_channel_returns_exact_valid_input_range_and_metadata(self):
        source = probe(seconds=12, sample_rate=44100)
        with tempfile.TemporaryDirectory(prefix="v4-aac-test-") as directory:
            result = process_channel(source, "AAC 128 kbps", Path(directory))

        self.assertEqual(result["audio"].sample_rate, source.sample_rate)
        self.assertEqual(result["audio"].samples.size, source.samples.size)
        self.assertEqual(result["encoded_metadata"]["sample_rate_hz"], source.sample_rate)
        self.assertEqual(result["encoded_metadata"]["channels"], 1)
        self.assertEqual(result["effective_sample_range_samples"], [0, source.samples.size])
        self.assertEqual(result["leading_samples_discarded"], 0)
        self.assertGreaterEqual(result["tail_padding_samples_removed"], 0)


if __name__ == "__main__":
    unittest.main()
