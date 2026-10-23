"""Container entry point for the unmodified Gradio demo.

Hosting provider supplies public HTTPS termination; this process listens only
on the internal container port. Do not turn on Gradio's public share links.
"""
from __future__ import annotations
import os
from app.gui import build_demo

def main() -> None:
    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    demo = build_demo()
    demo.queue(default_concurrency_limit=1, max_size=4)
    demo.launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.environ.get("PORT", os.environ.get("GRADIO_SERVER_PORT", "7860"))),
        share=False,
        inbrowser=False,
        max_file_size="16mb",
        show_error=False,
    )

if __name__ == "__main__":
    main()
