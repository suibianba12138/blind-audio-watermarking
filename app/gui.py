"""Small localhost Gradio interface for the public blind watermark demo."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from audio_watermark.course_v2 import embed_identity_multiblock

from .audio_io import decode_audio_file, prepare_for_demo, write_wav
from .mp3_codec import encode_decode_mp3
from .pipeline import _detect_in_subprocess
from .public_config import BLOCK_SECONDS, REJECTION_THRESHOLD, build_embedding_config, load_public_selector


IDENTITY_CHOICES = ["NO WATERMARK", "UESTC-001", "UESTC-002", "UESTC-003", "UESTC-004"]


def _duration_value(label: str) -> int:
    values = {"6 seconds": 6, "15 seconds": 15, "30 seconds": 30}
    try:
        return values[label]
    except KeyError as error:
        raise ValueError("duration must be 6, 15, or 30 seconds") from error


def _format_detection(result: dict[str, object]) -> str:
    status = result.get("status")
    if status == "IDENTIFIED":
        headline = f"DETECTED: {result.get('identity')}"
    elif status == "UNKNOWN":
        headline = "UNKNOWN / NO VALID WATERMARK"
    else:
        headline = f"DETECTOR ERROR: {result.get('error', 'unknown error')}"
    return "\n".join(
        [
            headline,
            f"distance: {result.get('minimum_distance', 'n/a')} / threshold: {result.get('rejection_threshold', REJECTION_THRESHOLD)}",
            f"blocks used: {result.get('block_count', 'n/a')}",
            f"duration: {result.get('duration_seconds', 'n/a')} s",
            f"confidence (diagnostic): {result.get('confidence', 'n/a')}",
        ]
    )


def _embed_action(input_path: str | None, identity: str, duration_label: str):
    if not input_path:
        return None, None, None, None, "请选择本地 WAV/音频文件。"
    try:
        duration = _duration_value(duration_label)
        session = Path(tempfile.mkdtemp(prefix="public_watermark_gui_"))
        source = prepare_for_demo(decode_audio_file(input_path), duration_seconds=duration)
        original_path = write_wav(session / "original_prepared.wav", source)
        if identity == "NO WATERMARK":
            marked = source.samples.copy()
            blocks = 0
        else:
            result = embed_identity_multiblock(
                source.samples,
                identity,
                build_embedding_config(),
                load_public_selector(),
                block_seconds=BLOCK_SECONDS,
            )
            marked = result.audio
            blocks = len(result.blocks)
        marked_path = write_wav(session / "watermarked.wav", marked, source.sample_rate)
        state = json.dumps({"marked_path": str(marked_path), "session": str(session)})
        info = (
            f"已生成 {identity}。准备时长 {source.samples.size / source.sample_rate:.1f} s；"
            f"实际嵌入时间块 {blocks}。检测器尚未读取 expected identity。"
        )
        return str(original_path), str(marked_path), state, None, info
    except Exception as error:
        return None, None, None, None, f"嵌入失败：{error}"


def _compress_action(state: str | None):
    if not state:
        return None, None, None, "请先完成嵌入。"
    try:
        payload = json.loads(state)
        marked_path = Path(payload["marked_path"])
        session = Path(payload["session"])
        marked = decode_audio_file(marked_path)
        mp3_path, decoded_path, _ = encode_decode_mp3(marked, session)
        next_state = json.dumps({"received_path": str(decoded_path), "session": str(session)})
        return str(mp3_path), str(decoded_path), next_state, "已完成真实 FFmpeg MP3 128 kbps 编码并解码。"
    except Exception as error:
        return None, None, None, f"MP3 失败：{error}"


def _detect_action(state: str | None):
    if not state:
        return "UNKNOWN / NO VALID WATERMARK\n请先完成嵌入或 MP3 压缩。"
    try:
        payload = json.loads(state)
        received_path = Path(payload["received_path"])
        result = _detect_in_subprocess(received_path)
        return _format_detection(result)
    except Exception as error:
        return f"DETECTOR ERROR: {error}"


def build_demo():
    """Construct the Gradio Blocks application without launching it."""

    try:
        import gradio as gr
    except ModuleNotFoundError as error:
        raise RuntimeError("GUI dependencies are missing; install requirements.txt") from error

    with gr.Blocks(title="Blind Audio Watermark Demo") as demo:
        gr.Markdown(
            "# Blind Audio Watermark Demo\n"
            "Course V2 public prototype · REAL_TOP32 · detector is blind and may reject as UNKNOWN"
        )
        with gr.Row():
            input_audio = gr.Audio(label="1. Upload audio", sources=["upload"], type="filepath")
            identity = gr.Dropdown(
                IDENTITY_CHOICES,
                value="UESTC-001",
                label="Identity (embedding only)",
            )
            duration = gr.Dropdown(
                ["6 seconds", "15 seconds", "30 seconds"],
                value="6 seconds",
                label="Prepared duration",
            )
        embed_button = gr.Button("Embed watermark", variant="primary")
        embed_info = gr.Textbox(label="Embedding status", interactive=False)
        with gr.Row():
            original_audio = gr.Audio(label="Original / prepared", type="filepath")
            watermarked_audio = gr.Audio(label="Watermarked", type="filepath")
        session_state = gr.State()
        compress_button = gr.Button("2. Encode real MP3 128 kbps")
        compression_info = gr.Textbox(label="Compression status", interactive=False)
        with gr.Row():
            compressed_mp3 = gr.Audio(label="Compressed MP3", type="filepath")
            compressed_wav = gr.Audio(label="Decoded MP3 audio", type="filepath")
        received_state = gr.State()
        detect_button = gr.Button("3. Blind detect", variant="primary")
        detector_output = gr.Textbox(label="Detection result", lines=5, interactive=False)
        gr.Markdown(
            "The detector receives only the selected received audio plus the public map/config. "
            "No expected identity, original audio, payload, filename, or cached answer is passed to it."
        )

        embed_button.click(
            _embed_action,
            inputs=[input_audio, identity, duration],
            outputs=[original_audio, watermarked_audio, session_state, received_state, embed_info],
        )
        compress_button.click(
            _compress_action,
            inputs=[session_state],
            outputs=[compressed_mp3, compressed_wav, received_state, compression_info],
        )
        detect_button.click(_detect_action, inputs=[received_state], outputs=[detector_output])
    return demo


def main() -> None:
    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    demo = build_demo()
    demo.launch(
        server_name="127.0.0.1",
        server_port=int(os.environ.get("GRADIO_SERVER_PORT", "7860")),
        share=False,
        inbrowser=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
