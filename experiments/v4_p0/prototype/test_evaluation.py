from audio_watermark.evaluation import DetectionEvidence, score_detection


def test_unified_scorer_separates_detection_from_message_recovery():
    evidence = DetectionEvidence(
        detected=True,
        recovered_message=(1, 0),
        confidence=0.8,
        presence_score=0.8,
        reject_reason=None,
    )
    row = score_detection(evidence, expected_message=(1, 1))
    assert row.detected is True
    assert row.correct_accepted_recovery is False
    assert row.wrong_message_acceptance is True
    assert row.logical_ber == 0.5


def test_unified_scorer_does_not_need_expected_message_for_detector():
    evidence = DetectionEvidence(
        detected=False,
        recovered_message=(0, 1),
        confidence=0.1,
        presence_score=0.1,
        reject_reason="below_threshold",
    )
    row = score_detection(evidence, expected_message=None)
    assert row.correct_accepted_recovery is None
    assert row.wrong_message_acceptance is None
