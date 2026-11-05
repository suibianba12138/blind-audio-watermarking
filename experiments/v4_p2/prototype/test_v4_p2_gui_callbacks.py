import tempfile
import unittest
from pathlib import Path
import numpy as np
import soundfile as sf
from app.v4_p2_gui import embed_callback, compress_callback, detect_callback
from app.v4_tempfiles import ArtifactStore


class FakeAdapter:
    def embed(self, audio, message, sample_rate):
        return {'audio': audio * 0.99, 'embedding_snr_db': 40.0, 'seconds': 0.01}
    def detect(self, audio, sample_rate):
        return {'state': 'UNKNOWN', 'candidate': None, 'confidence': None,
                'presence_calibration': 'PROVISIONAL', 'seconds': 0.02}


class GuiCallbackTests(unittest.TestCase):
    def test_embed_rejects_invalid_message_without_leaking_files(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); source=td/'source.wav'; sf.write(source, np.zeros(44100*12, np.float32), 44100)
            store=ArtifactStore(td/'out')
            result=embed_callback(str(source), 'not-hex', adapter=FakeAdapter(), store=store)
            self.assertEqual(result[3], '消息请输入恰好 10 位十六进制字符（5 字节）。')
            self.assertEqual(list(store.root.iterdir()), [])

    def test_embed_mp3_and_independent_negative_detection(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); source=td/'source.wav'; sf.write(source, np.random.default_rng(5).normal(0,.05,44100*12).astype(np.float32), 44100)
            store=ArtifactStore(td/'out')
            original,marked,download,status=embed_callback(str(source),'123456789A',adapter=FakeAdapter(),store=store)
            self.assertTrue(Path(download).is_file())
            self.assertIn('SNR 40.00 dB',status)
            mp3,decoded,mp3_download,decoded_download,codec_status=compress_callback(marked,store=store)
            self.assertTrue(Path(mp3).is_file())
            self.assertTrue(Path(decoded_download).is_file())
            detection=detect_callback(decoded_download,adapter=FakeAdapter())
            self.assertIn('判决：UNKNOWN',detection)
            self.assertIn('无消息候选',detection)
            store.cleanup()
            self.assertFalse(Path(original).exists())


if __name__ == '__main__':
    unittest.main()
