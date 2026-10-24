from __future__ import annotations

from scripts.v3_p2_v_independent_validation import mcnemar_two_sided, wilson_interval


def test_wilson_interval_reports_uncertainty_for_zero_rate() -> None:
    lower, upper = wilson_interval(0, 60)
    assert lower == 0.0
    assert 0.05 < upper < 0.07


def test_mcnemar_is_neutral_without_discordant_pairs() -> None:
    assert mcnemar_two_sided(0, 0) == 1.0
