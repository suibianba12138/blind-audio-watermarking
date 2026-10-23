"""Hugging Face Spaces/local entry point for the public Gradio app."""

from app.gui import build_demo


demo = build_demo()


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False, inbrowser=False)
