import unittest
import numpy as np

from app.silentcipher_adapter import (
    DECODE_ERROR, IDENTIFIED, UNKNOWN, PresencePolicy, SilentCipherAdapter,
    validate_message, classify_decode_result, sanitize_exception,
)


class FakeModel:
    def __init__(self, result=None, error=None):
        self.result = result or {"status": True, "messages": [[1, 2, 3, 4, 5]], "confidences": [0.9]}
        self.error = error

    def decode_wav(self, audio, sr, phase_shift_decoding=False):
        if self.error:
            raise self.error
        return self.result

    def encode_wav(self, audio, sr, message, calc_sdr=True):
        return audio.copy(), 40.0


class AdapterTests(unittest.TestCase):
    def test_message_requires_exactly_five_bytes(self):
        self.assertEqual(validate_message([0, 1, 2, 3, 255]), (0, 1, 2, 3, 255))
        with self.assertRaises(ValueError):
            validate_message([1, 2, 3, 4])
        with self.assertRaises(ValueError):
            validate_message([1, 2, 3, 4, 256])

    def test_official_status_is_not_presence_without_threshold(self):
        raw = classify_decode_result({"status": True, "messages": [[9, 8, 7, 6, 5]], "confidences": [0.404]})
        self.assertEqual(raw["state"], UNKNOWN)
        self.assertEqual(raw["candidate"], (9, 8, 7, 6, 5))

    def test_provisional_presence_threshold_accepts_only_confident_candidate(self):
        policy = PresencePolicy(threshold=0.680556, calibration="PROVISIONAL")
        accepted = SilentCipherAdapter(model=FakeModel(), presence_policy=policy).detect(np.full(44100, 0.01, np.float32))
        self.assertEqual(accepted["state"], IDENTIFIED)
        low_model = FakeModel(result={"status": True, "messages": [[1,2,3,4,5]], "confidences": [0.4]})
        rejected = SilentCipherAdapter(model=low_model, presence_policy=policy).detect(np.full(44100, 0.01, np.float32))
        self.assertEqual(rejected["state"], UNKNOWN)

    def test_decode_failure_and_python_exception_are_distinct_and_sanitized(self):
        no_candidate = SilentCipherAdapter(model=FakeModel(result={"status": False, "error": "Could not find message"})).detect(np.full(44100, 0.01, np.float32))
        self.assertEqual(no_candidate["state"], UNKNOWN)
        failure = sanitize_exception(RuntimeError("bad at [local path omitted]"))
        self.assertEqual(failure["state"], DECODE_ERROR)
        self.assertNotIn("/home/", str(failure))
        self.assertNotIn("alice", str(failure))

    def test_invalid_audio_is_rejected_before_model_call(self):
        adapter = SilentCipherAdapter(model=FakeModel())
        with self.assertRaises(ValueError):
            adapter.decode(np.array([np.nan], dtype=np.float32))
        with self.assertRaises(ValueError):
            adapter.decode(np.zeros(44100, dtype=np.float32))


if __name__ == '__main__':
    unittest.main()
