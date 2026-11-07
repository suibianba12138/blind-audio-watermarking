import tempfile
import time
import unittest
from pathlib import Path
import numpy as np
from app.silentcipher_diagnostics import parse_frame_predictions
from app.v4_tempfiles import ArtifactStore


class DiagnosticTests(unittest.TestCase):
    def test_missing_terminator_is_reported_at_parser_stage(self):
        values = np.tile(np.arange(1, 4), 7)
        result = parse_frame_predictions(values, 21)
        self.assertEqual(result['stage'], 'TERMINATOR')
        self.assertEqual(result['parse_error'], 'MISSING_TERMINATOR')
        self.assertIsNone(result['terminator_index'])


class TempStoreTests(unittest.TestCase):
    def test_job_paths_are_isolated_and_expired_jobs_are_cleaned(self):
        with tempfile.TemporaryDirectory() as td:
            store = ArtifactStore(Path(td) / 'private', ttl_seconds=60)
            job = store.new_job()
            target = store.checked_path(job, 'marked.wav')
            target.write_bytes(b'fake')
            self.assertEqual(target.read_bytes(), b'fake')
            with self.assertRaises(ValueError):
                store.checked_path(job, '../outside')
            shutil_root = store.root
            import shutil
            shutil.rmtree(shutil_root)
            recreated_job = store.new_job()
            self.assertTrue(recreated_job.is_dir())
            expired = store.new_job()
            import os
            os.utime(expired, (time.time()-100, time.time()-100))
            self.assertEqual(store.cleanup_expired(), 1)
            self.assertFalse(expired.exists())
            store.cleanup()
            self.assertFalse(store.root.exists())


if __name__ == '__main__':
    unittest.main()
