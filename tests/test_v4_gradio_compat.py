from __future__ import annotations

import warnings


def test_studio_builds_without_gradio6_moved_constructor_warning() -> None:
    from app.v4_studio_gui import build_demo

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        demo = build_demo()

    assert demo.config["components"]
    assert not any("moved from the Blocks constructor" in str(item.message) for item in caught)


def test_studio_design_contract_and_api_names() -> None:
    """Visual changes cannot silently remove any existing live API or tab."""
    from app.v4_studio_gui import build_demo
    from app.v4_studio_theme import STUDIO_CSS, STUDIO_HERO, STUDIO_FOOTER

    demo = build_demo()
    cfg = demo.config
    assert "nsk-hero" in STUDIO_CSS and "#fafafa" in STUDIO_CSS
    assert "nsk-hero__facts" in STUDIO_HERO
    assert "nsk-footer" in STUDIO_FOOTER
    assert "40 bit" in STUDIO_HERO
    names = {dep.get("api_name") for dep in cfg["dependencies"]}
    assert {"backend_info", "embed", "channel", "detect", "analyze"} <= names
    text = str(cfg["components"])
    assert all(name in text for name in ("Watermark", "Channel Lab",
                                         "Blind Detection", "Signal Analysis"))


def test_studio_static_html_does_not_load_remote_assets() -> None:
    """Navigation links may be external, but no remote JS, CSS or font is loaded."""
    from app.v4_studio_theme import STUDIO_CSS, STUDIO_HERO, STUDIO_FOOTER
    all_text = STUDIO_CSS + STUDIO_HERO + STUDIO_FOOTER
    assert "<script" not in all_text.lower()
    assert "@import" not in all_text.lower()
    assert "url(" not in STUDIO_CSS.lower()
