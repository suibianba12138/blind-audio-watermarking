from __future__ import annotations

from pathlib import Path


def test_acceptance_report_contains_required_gates(tmp_path: Path) -> None:
    from scripts.v3_p3_acceptance import run_acceptance

    report = run_acceptance(output_dir=tmp_path)

    assert report["blind_detection"] == "PASS"
    assert report["negative_unknown"] == "PASS"
    assert report["formal_perceptual_gate"] == "NOT_ESTABLISHED"
    assert report["render_feasibility"] == "LOCAL_PROXY_ONLY"
    assert report["cli_fallback"] == "PASS"
    assert report["size_duration_guards"] == "PASS"
    assert report["session_cleanup"] == "PASS"
