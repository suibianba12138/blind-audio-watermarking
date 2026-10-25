from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def test_acceptance_report_contains_required_gates(tmp_path: Path) -> None:
    import scripts.v3_p3_acceptance as acceptance

    report = acceptance.run_acceptance(output_dir=tmp_path)

    assert report["blind_detection"] == "PASS"
    assert report["negative_unknown"] == "PASS"
    assert report["formal_perceptual_gate"] == "NOT_ESTABLISHED"
    assert report["render_feasibility"] == "LOCAL_PROXY_ONLY"
    assert report["cli_fallback"] == "PASS"
    assert report["size_duration_guards"] == "PASS"
    assert report["session_cleanup"] == "PASS"
    assert report["mp3_roundtrip"] == "PASS"
    assert report["status"] == "PASS"


def test_missing_ffmpeg_blocks_overall_acceptance() -> None:
    from scripts.v3_p3_acceptance import _overall_status

    report = {
        "blind_detection": "PASS",
        "negative_unknown": "PASS",
        "wrong_key": "PASS",
        "invalid_input": "PASS",
        "size_duration_guards": "PASS",
        "session_cleanup": "PASS",
        "cli_fallback": "PASS",
        "mp3_roundtrip": "BLOCKED",
        "ffmpeg_available": False,
    }

    assert _overall_status(report) == "BLOCKED"
    assert _overall_status({**report, "mp3_roundtrip": "NOT_AVAILABLE"}) == "BLOCKED"


def test_missing_ffmpeg_run_writes_blocked_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import scripts.v3_p3_acceptance as acceptance

    monkeypatch.setattr(acceptance.shutil, "which", lambda _name: None)

    report = acceptance.run_acceptance(output_dir=tmp_path)

    assert report["status"] == "BLOCKED"
    assert report["mp3_roundtrip"] == "BLOCKED"
    assert report["blockers"] == ["FFMPEG_UNAVAILABLE"]
    assert (tmp_path / acceptance.REPORT_NAME).is_file()


@pytest.mark.parametrize(
    ("status", "message", "expected"),
    [
        ("UNKNOWN", None, True),
        ("IDENTIFIED", 173, False),
        ("IDENTIFIED", 42, False),
        ("UNKNOWN", 173, False),
    ],
)
def test_wrong_key_requires_unknown_without_message(
    status: str, message: int | None, expected: bool
) -> None:
    from scripts.v3_p3_acceptance import _wrong_key_result_passed

    assert _wrong_key_result_passed(status, message) is expected


def test_cli_timeout_is_reported_as_a_failed_fallback(monkeypatch, tmp_path: Path) -> None:
    import scripts.v3_p3_acceptance as acceptance

    def timeout(*args: object, **kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd="v3_demo", timeout=120)

    monkeypatch.setattr(acceptance.subprocess, "run", timeout)

    passed, detail = acceptance._run_cli(tmp_path / "input.wav", tmp_path / "output")

    assert passed is False
    assert "timed out" in detail


def test_unexpected_exception_writes_structured_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import scripts.v3_p3_acceptance as acceptance

    def fail_fixture(path: Path) -> Path:
        raise RuntimeError("injected acceptance failure")

    monkeypatch.setattr(acceptance, "_make_fixture", fail_fixture)

    report = acceptance.run_acceptance(output_dir=tmp_path)
    saved = tmp_path / acceptance.REPORT_NAME

    assert report["status"] == "FAIL"
    assert report["unexpected_exception"]["type"] == "RuntimeError"
    assert "injected acceptance failure" in report["unexpected_exception"]["message"]
    assert saved.is_file()
