from pathlib import Path

import numpy as np
from scipy.io import wavfile

from course_watermark.c2 import Config as C2Config
from course_watermark.c2 import detect as c2_detect
from course_watermark.c2 import embed as c2_embed
from course_watermark.c3 import Config as C3Config
from course_watermark.c3 import detect as c3_detect
from course_watermark.c3 import embed as c3_embed


FIXTURE = Path(__file__).parents[1] / "media" / "selected_c3_16_showcase" / "Original.wav"


def reference_block() -> np.ndarray:
    sample_rate, samples = wavfile.read(FIXTURE)
    assert sample_rate == 48_000
    assert samples.ndim == 1
    assert samples.dtype == np.float32
    block = samples[: 6 * sample_rate].astype(np.float64)
    assert block.size == 6 * sample_rate
    return block


def test_c2_public_key_roundtrip_on_real_music_reference():
    reference = reference_block()
    config = C2Config(key="course-demo-public-v1", target_snr_db=45.0)
    message = 0xA7
    watermarked = c2_embed(reference, message, config)
    detected = c2_detect(watermarked, reference, config)

    assert detected.message == message
    assert detected.presence_stat >= 0.6226488835443009
    assert detected.reference_similarity >= 0.5
    assert np.max(np.abs(watermarked)) <= 1.0


def test_c3_public_key_roundtrip_on_real_music_reference():
    reference = reference_block()
    config = C3Config(key="course-demo-public-v1", target_snr_db=45.0)
    message = 0xA7C3
    watermarked = c3_embed(reference, message, config)
    detected = c3_detect(watermarked, reference, config)

    assert detected.message == message
    assert detected.presence_stat >= 0.7199080718655814
    assert detected.reference_similarity >= 0.5
    assert np.max(np.abs(watermarked)) <= 1.0
