import inspect
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from app import v4_backends


class BackendTests(unittest.TestCase):
    def test_detector_signatures_have_no_reference_or_message(self):
        for function in (v4_backends.detect, v4_backends.detect_neural, v4_backends.detect_classic):
            names = tuple(inspect.signature(function).parameters)
            self.assertNotIn("message", names)
            self.assertNotIn("reference", names)
            self.assertNotIn("expected", names)

    def test_neural_backend_enforces_frozen_model_contract(self):
        with self.assertRaises(ValueError):
            v4_backends.embed_neural(np.zeros(44100 * 6), (1, 2, 3, 4, 5), 44100)

    def test_classic_backend_enforces_frozen_v3_contract(self):
        with self.assertRaises(ValueError):
            v4_backends.detect_classic(np.zeros(48000 * 12), 48000)

    def test_v3_adapter_loads_narrow_api_without_modifying_checkout(self):
        root = Path(os.environ["V3_SOURCE_ROOT"])
        api = v4_backends._v3_api()
        self.assertEqual(api.V3_PAYLOAD_BITS, 8)
        self.assertEqual(api.V3_DURATION_SECONDS, 6)
        self.assertEqual(Path(api.__file__).resolve(), (root / "app/v3_api.py").resolve())


if __name__ == "__main__":
    unittest.main()
