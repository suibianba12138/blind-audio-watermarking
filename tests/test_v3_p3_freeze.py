import json
from pathlib import Path


def test_v3_freeze_records_the_p2v_operating_point():
    data = json.loads(Path("configs/v3_8bit_candidate_freeze.json").read_text())

    assert data["stage"] == "V3_P3_V3_8BIT_CANDIDATE"
    assert data["strength"] == 1.60
    assert data["presence_threshold"] == 0.7855073980199624
    assert data["protocol"]["duration_seconds"] == 6
