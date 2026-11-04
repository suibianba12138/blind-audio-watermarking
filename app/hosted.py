"""Safe Render entrypoint: preserve Legacy unless V3 is explicitly enabled.

V3 + Legacy is the default UI on the NEXT manually approved Render deployment.
Setting V3_DEMO_ENABLED=0 restores Course V2 only without changing the algorithm.
"""
from __future__ import annotations

import os

def main() -> None:
    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    if os.environ.get("V3_DEMO_ENABLED", "1") == "1":
        from app.integration_gui import build_integration_demo
        demo = build_integration_demo()
    else:
        from app.gui import build_demo
        demo = build_demo()
    demo.queue(default_concurrency_limit=1, max_size=4, api_open=False)
    demo.launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.environ.get("PORT", os.environ.get("GRADIO_SERVER_PORT", "7860"))),
        share=False,
        inbrowser=False,
        max_file_size="16mb",
        show_error=False,
        blocked_paths=["/workspace", "/home", "/etc", "/root"],
    )

if __name__ == "__main__":
    main()
