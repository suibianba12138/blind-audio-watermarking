from __future__ import annotations

import warnings


def test_studio_builds_without_gradio6_moved_constructor_warning() -> None:
    from app.v4_studio_gui import build_demo

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        demo = build_demo()

    assert demo.config["components"]
    assert not any("moved from the Blocks constructor" in str(item.message) for item in caught)
