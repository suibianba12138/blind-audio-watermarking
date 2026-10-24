from v3_p2_capacity_pilot import (
    aggregate_pilot_metrics,
    calibrate_capacity_thresholds,
)


def test_capacity_thresholds_use_calibration_rows_only():
    rows = [
        {"method": "degree2_12", "p2_role": "calibration", "sample_role": "positive", "condition": "mp3_128k", "presence_score": 0.70},
        {"method": "degree2_12", "p2_role": "calibration", "sample_role": "negative", "condition": "clean_no_watermark", "presence_score": 0.10},
        {"method": "degree2_12", "p2_role": "pilot", "sample_role": "positive", "condition": "mp3_128k", "presence_score": 0.99},
        {"method": "degree2_16", "p2_role": "calibration", "sample_role": "positive", "condition": "mp3_128k", "presence_score": 0.70},
        {"method": "degree2_16", "p2_role": "calibration", "sample_role": "negative", "condition": "clean_no_watermark", "presence_score": 0.10},
    ]
    thresholds = calibrate_capacity_thresholds(rows)
    assert thresholds["degree2_12"]["source_role"] == "calibration"
    assert thresholds["degree2_12"]["threshold"] != 0.99


def test_pilot_metrics_distinguish_exact_recovery_from_acceptance():
    rows = [
        {"method": "degree2_12", "p2_role": "pilot", "record_id": "src-1", "sample_role": "positive", "condition": "mp3_128k", "presence_accepted": 1, "decoded_exact": 1, "wrong_message_acceptance": 0, "physical_raw_ber": 0.0, "logical_ber": 0.0},
        {"method": "degree2_12", "p2_role": "pilot", "record_id": "src-1", "sample_role": "positive", "condition": "mp3_128k", "presence_accepted": 1, "decoded_exact": 0, "wrong_message_acceptance": 1, "physical_raw_ber": 0.1, "logical_ber": 0.1},
        {"method": "degree2_12", "p2_role": "pilot", "record_id": "src-1", "sample_role": "negative", "condition": "clean_mp3_no_watermark", "presence_accepted": 0, "decoded_exact": "NOT_APPLICABLE", "wrong_message_acceptance": "NOT_APPLICABLE"},
    ]
    metrics = aggregate_pilot_metrics(rows, "degree2_12")
    assert metrics["positive_trials"] == 2
    assert metrics["accepted_trials"] == 2
    assert metrics["exact_recovery_trials"] == 1
    assert metrics["wrong_message_acceptance_trials"] == 1
    assert metrics["negative_trials"] == 1
    assert metrics["source_recordings"] == 1
    assert metrics["source_both_messages_exact"] == 0
