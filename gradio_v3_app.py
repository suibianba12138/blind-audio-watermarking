"""Localhost-only launcher for the V3/Course V2 integration GUI."""

from __future__ import annotations

import os

from app.integration_gui import build_integration_demo


def main() -> None:
    """Launch the integration UI without creating a public share link."""

    port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    demo = build_integration_demo()
    demo.queue(default_concurrency_limit=1, max_size=4)
    demo.launch(
        server_name="127.0.0.1",
        server_port=port,
        share=False,
        inbrowser=False,
        max_file_size="16mb",
        show_error=True,
    )


if __name__ == "__main__":
    main()
