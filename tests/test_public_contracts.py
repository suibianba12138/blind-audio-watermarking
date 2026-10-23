from __future__ import annotations

from pathlib import Path

from app.detector_worker import _parser
from app.public_config import REAL_TOP32_MAP_SHA256, load_public_selector


def test_public_map_and_selector_contract() -> None:
    selector = load_public_selector()
    assert selector.top_k == 32
    assert selector.map_sha256 == REAL_TOP32_MAP_SHA256
    assert len(selector.selected_group_ids) == 32


def test_detector_cli_has_no_expected_answer_arguments() -> None:
    options = {action.dest for action in _parser()._actions}
    assert {"input", "map", "json"}.issubset(options)
    assert not options.intersection({"expected", "clean", "payload", "cache", "identity"})


def test_public_source_has_no_personal_absolute_path() -> None:
    root = Path(__file__).parents[1]
    checked = list((root / "app").rglob("*.py")) + list((root / "scripts").rglob("*.py"))
    checked += list((root / "src").rglob("*.py"))
    private_marker = "/" + "home/" + "nsk/"
    assert all(private_marker not in path.read_text(encoding="utf-8") for path in checked)
